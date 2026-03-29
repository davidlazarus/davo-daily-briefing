"""
Plaud integration — fetches recent meeting transcripts and summaries.
Uses the Plaud web API (reverse-engineered from web.plaud.ai).
Auth token obtained from web.plaud.ai → DevTools → Local Storage → tokenstr.
"""

import os
import requests
from datetime import datetime, timedelta


BASE_URL = "https://api.plaud.ai"


def get_headers():
    token = os.getenv("PLAUD_AUTH_TOKEN", "")
    # Strip "bearer " prefix if present — the env var might include it
    if token.lower().startswith("bearer "):
        token = token[7:]
    return {
        "Authorization": f"bearer {token}",
        "Content-Type": "application/json",
        "App-Platform": "web",
        "Edit-From": "web",
        "Origin": "https://web.plaud.ai",
        "Referer": "https://web.plaud.ai/",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
    }


def fetch_plaud_notes(hours_back: int = 48, max_results: int = 10) -> list[dict]:
    """
    Fetch recent Plaud recordings with transcripts and summaries.
    Uses the /file/simple/web endpoint (the real Plaud web API).
    """
    headers = get_headers()

    try:
        # Fetch recordings list — this is the actual endpoint Plaud's web app uses
        response = requests.get(
            f"{BASE_URL}/file/simple/web",
            headers=headers,
            params={
                "skip": 0,
                "limit": max_results,
                "is_trash": 2,  # 2 = not trash
                "sort_by": "start_time",
                "is_desc": "true",
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        import logging
        logging.getLogger('briefing-agent').error(f'Plaud raw error: {e}')
        return [{"title": "Plaud API error", "error": str(e), "summary": f"Could not connect to Plaud: {str(e)}"}]

    import logging
    logging.getLogger("briefing-agent").info(f"Plaud raw response keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
    logging.getLogger("briefing-agent").info(f"Plaud raw response (first 500): {str(data)[:500]}")
    # The response structure — extract the recordings list
    # Try common response shapes
    records = []
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict):
        # Try various keys where records might live
        for key in ["data", "files", "records", "items", "list"]:
            candidate = data.get(key)
            if isinstance(candidate, list):
                records = candidate
                break
            elif isinstance(candidate, dict):
                # Nested: data.records, data.files, etc.
                for subkey in ["records", "files", "items", "list"]:
                    sub = candidate.get(subkey)
                    if isinstance(sub, list):
                        records = sub
                        break
                if records:
                    break

    if not records:
        # Return the raw response keys for debugging
        if isinstance(data, dict):
            return [{"title": "Plaud: no records found", "summary": f"Response keys: {list(data.keys())}", "date": ""}]
        return [{"title": "Plaud: unexpected response format", "summary": str(data)[:300], "date": ""}]

    cutoff = datetime.now() - timedelta(hours=hours_back)
    parsed = []

    for record in records:
        if not isinstance(record, dict):
            continue

        # Try to find timestamp — Plaud may use various field names
        created_at = ""
        for time_key in ["start_time", "created_at", "create_time", "date", "updated_at"]:
            val = record.get(time_key)
            if val:
                # Could be a unix timestamp (int) or ISO string
                if isinstance(val, (int, float)):
                    created_at = datetime.fromtimestamp(val).isoformat()
                else:
                    created_at = str(val)
                break

        # Filter by recency
        try:
            if isinstance(record.get("start_time"), (int, float)):
                record_time = datetime.fromtimestamp(record["start_time"])
            else:
                record_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            if record_time.replace(tzinfo=None) < cutoff:
                continue
        except (ValueError, TypeError, OSError):
            pass  # Include if we can't parse the date

        # Extract title — try various field names
        title = ""
        for title_key in ["title", "name", "file_name", "filename"]:
            if record.get(title_key):
                title = record[title_key]
                break
        title = title or "Untitled Recording"

        # Extract summary/transcript
        summary = ""
        for summary_key in ["summary", "transcript", "content", "text", "description", "note"]:
            if record.get(summary_key):
                summary = record[summary_key]
                break

        parsed.append({
            "title": title,
            "date": created_at,
            "summary": summary or "No summary available",
            "duration_seconds": record.get("duration", record.get("length", 0)),
        })

    return parsed if parsed else [{"title": "No recent Plaud recordings", "summary": "No recordings in the last 48 hours", "date": ""}]
