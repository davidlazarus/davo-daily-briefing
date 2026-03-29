"""
Davo's Daily Briefing Agent — Main Orchestrator
================================================
Runs on Railway via cron. Fetches data from all sources,
generates a briefing via Claude, and emails it at 5am AEST.

Usage:
  python main.py          # Run briefing now (manual trigger)
  python main.py --serve  # Start the scheduler (for Railway)
  python main.py --test   # Dry run — print briefing to console, don't email
"""

import os
import sys
import logging
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("briefing-agent")


def run_briefing(dry_run: bool = False):
    """
    Main briefing pipeline:
    1. Determine target date (today)
    2. Fetch data from all sources (with graceful fallbacks)
    3. Generate briefing via AI
    4. Send via email (or print if dry_run)
    """
    target_date = date.today()
    date_str = target_date.strftime("%A, %B %d, %Y")
    logger.info(f"Generating briefing for {date_str}")

    # --- 1. Fetch from all sources (each handles its own errors) ---
    calendar_events = _safe_fetch("Google Calendar", _fetch_calendar, target_date)
    emails = _safe_fetch("Gmail", _fetch_gmail)
    trello_tasks = _safe_fetch("Trello", _fetch_trello, target_date)
    plaud_notes = _safe_fetch("Plaud", _fetch_plaud)

    # --- 2. Generate briefing ---
    logger.info("Synthesizing briefing with AI...")
    from briefing_generator import generate_briefing

    briefing_text = generate_briefing(
        calendar_events=calendar_events,
        emails=emails,
        trello_tasks=trello_tasks,
        plaud_notes=plaud_notes,
        target_date=target_date,
    )

    if dry_run:
        print("\n" + "=" * 60)
        print(f"  BRIEFING FOR {date_str}")
        print("=" * 60)
        print(briefing_text)
        print("=" * 60)
        return briefing_text

    # --- 3. Send email ---
    logger.info("Sending briefing email...")
    from integrations.email_sender import send_briefing_email

    success = send_briefing_email(briefing_text, date_str)
    if success:
        logger.info("Briefing sent successfully!")
    else:
        logger.error("Failed to send briefing email.")

    return briefing_text


def _safe_fetch(source_name: str, fetch_fn, *args):
    """Wrapper that catches errors so one failed source doesn't kill the whole briefing."""
    try:
        logger.info(f"Fetching from {source_name}...")
        result = fetch_fn(*args)
        logger.info(f"  ✓ {source_name}: got {len(result) if isinstance(result, list) else 'data'}")
        return result
    except Exception as e:
        logger.warning(f"  ✗ {source_name} failed: {str(e)}")
        return [] if "list" in str(type(fetch_fn.__annotations__.get("return", ""))) else []


def _fetch_calendar(target_date):
    from integrations.google_calendar import fetch_calendar_events
    return fetch_calendar_events(target_date)


def _fetch_gmail():
    from integrations.gmail import fetch_recent_emails
    return fetch_recent_emails(hours_back=24, max_results=15)


def _fetch_trello(target_date):
    from integrations.trello import fetch_trello_tasks
    return fetch_trello_tasks(target_date)


def _fetch_plaud():
    from integrations.plaud import fetch_plaud_notes
    return fetch_plaud_notes(hours_back=48)


def start_scheduler():
    """Start APScheduler for Railway — runs the briefing daily at configured time."""
    from apscheduler.schedulers.blocking import BlockingScheduler
    import pytz

    tz_name = os.getenv("TIMEZONE", "Australia/Melbourne")
    hour = int(os.getenv("BRIEFING_HOUR", "5"))
    minute = int(os.getenv("BRIEFING_MINUTE", "0"))
    tz = pytz.timezone(tz_name)

    scheduler = BlockingScheduler(timezone=tz)
    scheduler.add_job(
        run_briefing,
        trigger="cron",
        hour=hour,
        minute=minute,
        id="daily_briefing",
        name="Davo's Daily Briefing",
        misfire_grace_time=3600,  # If missed, still run within 1 hour
    )

    logger.info(f"Scheduler started. Briefing will run daily at {hour:02d}:{minute:02d} {tz_name}")
    logger.info("Press Ctrl+C to stop.")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    if "--serve" in sys.argv:
        start_scheduler()
    elif "--test" in sys.argv:
        run_briefing(dry_run=True)
    else:
        run_briefing()
