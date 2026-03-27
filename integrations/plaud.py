"""
Plaud integration — fetches recent meeting transcripts and summaries.
Uses the unofficial Plaud API (reverse-engineered endpoints).
Auth token obtained from web.plaud.ai → DevTools → Local Storage → tokenstr.
"""

import os
import requests
from datetime import datetime, timedelta


BASE_URL = "https://api.plaud.ai"


def get_headers():
    token = os.getenv("PLAUD_AUTH_TOKEN")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "DavoBriefingAgent/1.0",
    }


def fetch_plaud_notes(hours_back: int = 48, max_results: int = 10) -> list[dict]:
    """
    Fetch recent Plaud recordings with transcripts and summaries.
    Returns list of dicts: title, date, transcript_summary, duration, speakers.

    Note: The Plaud API endpoints below are based on the unofficial reverse-engineered
    client. If they change, check https://github.com/arbuzmell/plaud-api for updates.
    """
    headers = get_headers()

    try:
        # Fetch recordings list
        response = requests.get(
            f"{BASE_URL}/api/v1/records",
            headers=headers,
            params={
                "page": 1,
                "page_size": max_results,
                "order": "desc",
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        return [{"title": "Plaud API error", "error": str(e)}]

    records = data.get("data", {}).get("records", [])
    cutoff = datetime.now() - timedelta(hours=hours_back)
    parsed = []

    for record in records:
        # Parse the record timestamp
        created_at = record.get("created_at", "")
        try:
            record_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            if record_time.replace(tzinfo=None) < cutoff:
                continue
        except (ValueError, TypeError):
            pass  # Include if we can't parse the date

        # Fetch the summary/transcript for this recording
        record_id = record.get("id")
        summary_text = ""

        if record_id:
            try:
                detail_resp = requests.get(
                    f"{BASE_URL}/api/v1/records/{record_id}/summary",
                    headers=headers,
                    timeout=30,
                )
                if detail_resp.ok:
                    summary_data = detail_resp.json()
                    summary_text = summary_data.get("data", {}).get("summary", "")
            except requests.RequestException:
                summary_text = "(Could not fetch summary)"

        parsed.append({
            "title": record.get("title", "Untitled Recording"),
            "date": created_at,
            "summary": summary_text or record.get("summary", "No summary available"),
            "duration_seconds": record.get("duration", 0),
            "speakers": record.get("speakers", []),
        })

    return parsed
