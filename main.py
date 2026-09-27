import os
from fastapi import FastAPI, Form, Request
from fastapi.responses import PlainTextResponse, RedirectResponse
from dotenv import load_dotenv

load_dotenv()

from app import google_auth
from app.claude_router import handle_message
from app.scheduler import start_scheduler

app = FastAPI(title="Jarvis")


@app.on_event("startup")
def _startup():
    start_scheduler()


@app.get("/")
def health():
    return {"status": "Jarvis is running", "google_connected": google_auth.is_authorized()}


# ---------- Google OAuth (visit once from your phone browser) ----------

@app.get("/auth/google")
def auth_google():
    return RedirectResponse(google_auth.build_auth_url())


@app.get("/auth/google/callback")
def auth_google_callback(code: str):
    google_auth.exchange_code_for_token(code)
    return PlainTextResponse("Google account connected. You can close this tab and go back to WhatsApp.")


# ---------- WhatsApp webhook (set this URL in Twilio console) ----------

@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request, Body: str = Form(...), From: str = Form(...)):
    reply_text = handle_message(Body)

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response><Message>{_escape_xml(reply_text)}</Message></Response>"""
    return PlainTextResponse(content=twiml, media_type="application/xml")


def _escape_xml(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
