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


def fetch_plaud_notes(hours_back: int = 96, max_results: int = 10) -> list[dict]:
    """
    Fetch recent Plaud recordings with transcripts and summaries.
    Uses /file/simple/web for the list, then /file/detail for each record.
    """
    headers = get_headers()

    try:
        response = requests.get(
            f"{BASE_URL}/file/simple/web",
            headers=headers,
            params={
                "skip": 0,
                "limit": max_results,
                "is_trash": 2,
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
    log = logging.getLogger("briefing-agent")
    log.info(f"Plaud raw response keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
    log.info(f"Plaud raw response (first 500): {str(data)[:500]}")

    records = data.get("data_file_list", [])
    if not records:
        return [{"title": "No Plaud recordings found", "summary": "API returned empty list", "date": ""}]

    cutoff = datetime.now() - timedelta(hours=hours_back)
    parsed = []

    for record in records:
        if not isinstance(record, dict):
            continue

        # Parse timestamp — Plaud uses unix timestamps in start_time
        start_time = record.get("start_time") or record.get("edit_time") or record.get("version")
        if isinstance(start_time, (int, float)):
            # Plaud sometimes uses milliseconds
            if start_time > 1e12:
                start_time = start_time / 1000
            record_time = datetime.fromtimestamp(start_time)
            created_at = record_time.isoformat()
            if record_time < cutoff:
                continue
        else:
            created_at = ""

        title = record.get("filename") or record.get("title") or record.get("name") or "Untitled Recording"
        record_id = record.get("id", "")

        # Try to fetch the detailed record (which has the summary/transcript)
        summary = ""
        if record_id:
            try:
                detail_resp = requests.get(
                    f"{BASE_URL}/file/{record_id}/detail",
                    headers=headers,
                    timeout=15,
                )
                if detail_resp.status_code == 200:
                    detail = detail_resp.json()
                    # Look for summary in various locations
                    detail_data = detail.get("data", detail)
                    summary = (
                        detail_data.get("summary")
                        or detail_data.get("ai_summary")
                        or detail_data.get("note")
                        or detail_data.get("transcript", "")[:500]
                        or ""
                    )
                    if not summary:
                        log.info(f"Plaud detail keys for {record_id}: {list(detail_data.keys())}")
            except Exception as e:
                log.warning(f"Plaud detail fetch failed for {record_id}: {e}")

        parsed.append({
            "title": title,
            "date": created_at,
            "summary": summary or "No summary available — check Plaud app for full transcript",
            "duration_seconds": record.get("duration", record.get("length", 0)),
        })

    return parsed if parsed else [{"title": "No recent Plaud recordings", "summary": f"No recordings in the last {hours_back} hours", "date": ""}]
