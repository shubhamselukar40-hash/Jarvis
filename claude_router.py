"""
The "brain" of Jarvis. Sends the user's WhatsApp message to Claude with a set
of tools (functions Jarvis can perform). Claude decides which tool to call
(or just replies conversationally), then we execute it and return the result
as the WhatsApp reply.
"""
import os
import json
import anthropic

from app.integrations import gmail_service, calendar_service
from app.scheduler import add_reminder

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

MODEL = "claude-sonnet-4-6"

TOOLS = [
    {
        "name": "summarize_unread_email",
        "description": "Fetch and summarize the user's recent unread emails.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_results": {"type": "integer", "description": "How many emails, default 8"}
            },
        },
    },
    {
        "name": "list_upcoming_events",
        "description": "List the user's upcoming calendar events.",
        "input_schema": {
            "type": "object",
            "properties": {
                "hours_ahead": {"type": "integer", "description": "Look-ahead window in hours, default 24"}
            },
        },
    },
    {
        "name": "create_calendar_event",
        "description": "Create a new calendar event.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "start_iso": {"type": "string", "description": "ISO 8601 datetime with timezone offset"},
                "end_iso": {"type": "string", "description": "ISO 8601 datetime with timezone offset"},
                "description": {"type": "string"},
            },
            "required": ["summary", "start_iso", "end_iso"],
        },
    },
    {
        "name": "set_reminder",
        "description": "Set a one-off or recurring reminder that Jarvis will message the user about later.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "What to remind the user of"},
                "run_at_iso": {"type": "string", "description": "ISO datetime for a one-off reminder"},
                "interval_minutes": {"type": "integer", "description": "For recurring reminders, e.g. water every 120 min"},
            },
            "required": ["message"],
        },
    },
]

SYSTEM_PROMPT = (
    "You are Jarvis, the user's personal background assistant reachable over WhatsApp. "
    "Be concise and practical - replies are read on a phone. "
    "Use the available tools whenever the user's request maps to one of them. "
    "If it's just a question or chat, answer directly without a tool. "
    "After a tool result comes back, summarize it naturally instead of dumping raw data."
)


def _execute_tool(name: str, tool_input: dict) -> str:
    if name == "summarize_unread_email":
        emails = gmail_service.get_recent_unread(tool_input.get("max_results", 8))
        return json.dumps(emails)
    if name == "list_upcoming_events":
        events = calendar_service.list_upcoming(hours_ahead=tool_input.get("hours_ahead", 24))
        return json.dumps(events)
    if name == "create_calendar_event":
        link = calendar_service.create_event(
            tool_input["summary"],
            tool_input["start_iso"],
            tool_input["end_iso"],
            tool_input.get("description", ""),
        )
        return json.dumps({"status": "created", "link": link})
    if name == "set_reminder":
        add_reminder(
            message=tool_input["message"],
            run_at_iso=tool_input.get("run_at_iso"),
            interval_minutes=tool_input.get("interval_minutes"),
        )
        return json.dumps({"status": "reminder scheduled"})
    return json.dumps({"error": f"unknown tool {name}"})


def handle_message(user_text: str) -> str:
    messages = [{"role": "user", "content": user_text}]

    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        tools=TOOLS,
        messages=messages,
    )

    # Loop in case Claude chains a tool call then wants to respond with text
    while response.stop_reason == "tool_use":
        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                try:
                    result = _execute_tool(block.name, block.input)
                except Exception as e:
                    result = json.dumps({"error": str(e)})
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": result}
                )
        messages.append({"role": "user", "content": tool_results})
        response = client.messages.create(
            model=MODEL, max_tokens=1000, system=SYSTEM_PROMPT, tools=TOOLS, messages=messages
        )

    text_parts = [b.text for b in response.content if b.type == "text"]
    return "\n".join(text_parts) if text_parts else "Done."
