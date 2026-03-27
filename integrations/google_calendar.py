"""
Google Calendar integration — fetches tomorrow's events.
Uses OAuth2 with a refresh token (no interactive browser flow needed on server).
"""

import os
import datetime
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
    tz = os.getenv("TIMEZONE", "Australia/Melbourne")
    time_min = f"{target_date.isoformat()}T00:00:00"
    time_max = f"{target_date.isoformat()}T23:59:59"

    events_result = service.events().list(
        calendarId="primary",
        timeMin=f"{time_min}+11:00",  # AEST offset — will refine with pytz
        timeMax=f"{time_max}+11:00",
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
