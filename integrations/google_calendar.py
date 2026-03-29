"""
Google Calendar integration — fetches today's events.
Uses OAuth2 with a refresh token (no interactive browser flow needed on server).
"""

import os
import datetime
import pytz
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def get_credentials():
    """Build credentials from environment variables (refresh token flow)."""
    return Credentials(
        token=None,
        refresh_token=os.getenv("GOOGLE_REFRESH_TOKEN"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        scopes=SCOPES,
    )


def fetch_calendar_events(target_date: datetime.date = None) -> list[dict]:
    """
    Fetch all calendar events for the target date.
    Returns a list of dicts with: summary, start, end, location, description.
    """
    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)

    if target_date is None:
        target_date = datetime.date.today() + datetime.timedelta(days=1)

    # Build time range: midnight to midnight in local tz
    tz = os.getenv("TIMEZONE", "Europe/Zurich")
    local_tz = pytz.timezone(tz)
    start_dt = local_tz.localize(datetime.datetime.combine(target_date, datetime.time.min))
    end_dt = local_tz.localize(datetime.datetime.combine(target_date, datetime.time(23, 59, 59)))

    events_result = service.events().list(
        calendarId="primary",
        timeMin=start_dt.isoformat(),
        timeMax=end_dt.isoformat(),
        maxResults=50,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = events_result.get("items", [])
    parsed = []

    for event in events:
        start = event["start"].get("dateTime", event["start"].get("date"))
        end = event["end"].get("dateTime", event["end"].get("date"))
        parsed.append({
            "summary": event.get("summary", "No title"),
            "start": start,
            "end": end,
            "location": event.get("location", ""),
            "description": event.get("description", ""),
            "attendees": [
                a.get("email", "") for a in event.get("attendees", [])
            ],
        })

    return parsed
