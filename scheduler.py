import json
import os
import uuid
import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

REMINDERS_PATH = "reminders.json"
scheduler = BackgroundScheduler()


def _send(message: str):
    # imported here to avoid a circular import with whatsapp module at load time
    from app.integrations.whatsapp import send_whatsapp
    send_whatsapp(f"⏰ Reminder: {message}")


def _load():
    if not os.path.exists(REMINDERS_PATH):
        return []
    with open(REMINDERS_PATH) as f:
        return json.load(f)


def _save(reminders):
    with open(REMINDERS_PATH, "w") as f:
        json.dump(reminders, f, indent=2)


def add_reminder(message: str, run_at_iso: str | None = None, interval_minutes: int | None = None):
    job_id = str(uuid.uuid4())
    record = {
        "id": job_id,
        "message": message,
        "run_at_iso": run_at_iso,
        "interval_minutes": interval_minutes,
    }
    reminders = _load()
    reminders.append(record)
    _save(reminders)
    _schedule_job(record)
    return job_id


def _schedule_job(record: dict):
    if record.get("interval_minutes"):
        scheduler.add_job(
            _send,
            trigger=IntervalTrigger(minutes=record["interval_minutes"]),
            args=[record["message"]],
            id=record["id"],
            replace_existing=True,
        )
    elif record.get("run_at_iso"):
        run_time = datetime.datetime.fromisoformat(record["run_at_iso"])
        scheduler.add_job(
            _send,
            trigger=DateTrigger(run_date=run_time),
            args=[record["message"]],
            id=record["id"],
            replace_existing=True,
        )


def start_scheduler():
    """Call once at app startup - reloads any reminders saved before a restart."""
    for record in _load():
        try:
            _schedule_job(record)
        except Exception:
            pass  # skip reminders whose time already passed
    scheduler.start()
