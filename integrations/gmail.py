"""
Gmail integration — fetches recent important/unread emails.
Pulls subject lines, senders, and snippets to surface in the briefing.
"""

import os
import datetime
import base64
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def get_credentials():
    return Credentials(
        token=None,
        refresh_token=os.getenv("GOOGLE_REFRESH_TOKEN"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        scopes=SCOPES,
    )


def fetch_recent_emails(hours_back: int = 24, max_results: int = 15) -> list[dict]:
    """
    Fetch recent unread or important emails from the last N hours.
    Returns list of dicts: subject, sender, snippet, date, labels.
    """
    creds = get_credentials()
    service = build("gmail", "v1", credentials=creds)

    # Build search query: recent + (unread OR important)
    after_ts = int(
        (datetime.datetime.now() - datetime.timedelta(hours=hours_back)).timestamp()
    )
    query = f"after:{after_ts} (is:unread OR is:important) -category:promotions -category:social"

    results = service.users().messages().list(
        userId="me", q=query, maxResults=max_results
    ).execute()

    messages = results.get("messages", [])
    parsed = []

    for msg_ref in messages:
        msg = service.users().messages().get(
            userId="me", id=msg_ref["id"], format="metadata",
            metadataHeaders=["Subject", "From", "Date"],
        ).execute()

        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        parsed.append({
            "subject": headers.get("Subject", "(no subject)"),
            "sender": headers.get("From", "Unknown"),
            "snippet": msg.get("snippet", ""),
            "date": headers.get("Date", ""),
            "labels": msg.get("labelIds", []),
        })

    return parsed
