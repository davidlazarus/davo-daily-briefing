"""
Briefing generator — takes all data sources and synthesizes
a daily briefing using Anthropic Claude.
"""

import os
from datetime import date, timedelta
import anthropic

from schedule import get_fixed_blocks, format_blocks_for_prompt, is_arlo_day
from storage import save_briefing


SYSTEM_PROMPT = """You are Davo's personal daily briefing agent. You produce a concise,
actionable morning briefing for the day ahead.

Davo is the CMO & CTO at Koja d'Or, and Creative Officer at Creatives.
He's training for UTMB (ultra trail marathon). He has a dog and a son named Arlo.

Your briefing style:
- Direct and concise. No fluff, no motivational quotes.
- Use bullet points for quick scanning
- Flag conflicts or tight transitions between meetings
- Suggest optimal time blocks for deep work
- Note anything urgent from email or Plaud notes
- Keep it under 500 words unless there's a lot going on

Note: UTMB training sessions from RUNNA sync to Google Calendar, so they'll appear
as calendar events. Flag them clearly in the schedule as training blocks.

Structure:
1. 🌅 Day at a Glance (one-liner summary of the day's vibe)
2. 📅 Schedule (chronological: meetings + training + fixed blocks merged)
3. ✅ Top Priorities (from Trello, max 5)
4. 📧 Email Highlights (anything needing attention)
5. 🎙️ Plaud Notes (any recent meeting takeaways worth remembering)
6. 💡 Heads Up (conflicts, tight windows, things to prep for)
"""

SECTION_KEYWORDS = {
    "calendar": ["schedule", "calendar"],
    "email": ["email", "inbox"],
    "tasks": ["top priorities", "priorities", "trello", "tasks"],
    "recordings": ["plaud", "recordings", "notes"],
    "health": ["health", "vitals", "training"],
    "synthesis": ["day at a glance", "heads up", "synthesis", "glance"],
}


def generate_briefing(
    calendar_events: list[dict],
    emails: list[dict],
    trello_tasks: list[dict],
    plaud_notes: list[dict],
    target_date: date = None,
) -> str:
    """
    Synthesize all data sources into a single daily briefing.
    Returns formatted briefing text (HTML-friendly for email).
    """
    if target_date is None:
        target_date = date.today() + timedelta(days=1)

    fixed_blocks = get_fixed_blocks(target_date)
    blocks_text = format_blocks_for_prompt(fixed_blocks)
    arlo_day = is_arlo_day(target_date)

    # Build the data payload for the AI
    user_prompt = f"""Generate Davo's briefing for {target_date.strftime('%A, %B %d, %Y')}.

{'🧒 This is an Arlo day.' if arlo_day else '🧒 Not an Arlo day (Lily has him on Fridays, otherwise Arlo is with his mum).'}

## Fixed Personal Blocks (non-negotiable)
{blocks_text}

## Calendar Events
{_format_calendar(calendar_events)}

## Trello Tasks for {target_date.strftime('%A')}
{_format_trello(trello_tasks)}

## Recent Emails (last 24h, unread/important)
{_format_emails(emails)}

## Recent Plaud Meeting Notes
{_format_plaud(plaud_notes)}

---
Now synthesize this into the daily briefing. Merge the fixed personal blocks with calendar
events into one chronological schedule. Flag any conflicts. RUNNA training sessions will
appear as calendar events — flag them clearly as training. Keep it tight and useful.
"""

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=2000,
    )

    raw_markdown = response.content[0].text
    sections = _parse_sections(raw_markdown)
    save_briefing(target_date, sections, raw_markdown)
    return raw_markdown


def _parse_sections(markdown: str) -> dict:
    parsed: dict[str, str] = {}
    current_header = None
    current_lines = []

    for line in markdown.splitlines():
        if line.startswith("## "):
            if current_header is not None:
                parsed[current_header] = "\n".join(current_lines).strip()
            current_header = line[3:].strip()
            current_lines = []
            continue
        current_lines.append(line)

    if current_header is not None:
        parsed[current_header] = "\n".join(current_lines).strip()

    normalized = {key: "" for key in SECTION_KEYWORDS}
    for header, body in parsed.items():
        target_key = _section_key_for_header(header)
        normalized[target_key] = body

    if not parsed:
        normalized["synthesis"] = markdown.strip()

    return normalized


def _section_key_for_header(header: str) -> str:
    lower_header = header.lower()
    for key, keywords in SECTION_KEYWORDS.items():
        if any(keyword in lower_header for keyword in keywords):
            return key
    return "synthesis"


def _format_calendar(events: list[dict]) -> str:
    if not events:
        return "  No calendar events."
    lines = []
    for e in events:
        attendees = f" (with: {', '.join(e['attendees'][:3])})" if e.get("attendees") else ""
        location = f" @ {e['location']}" if e.get("location") else ""
        lines.append(f"  - {e['start']} → {e['end']}: {e['summary']}{location}{attendees}")
    return "\n".join(lines)


def _format_trello(tasks: list[dict]) -> str:
    if not tasks:
        return "  No tasks scheduled."
    # Group tasks by category (KJD = Koja d'Or, CRTVS = Creatives, ALP, PERSO = Personal)
    from collections import defaultdict
    by_category = defaultdict(list)
    for t in tasks:
        by_category[t.get("category", "Uncategorized")].append(t)

    lines = []
    for category, cat_tasks in by_category.items():
        lines.append(f"\n  [{category}]")
        for t in cat_tasks:
            labels = f" [{', '.join(t['labels'])}]" if t.get("labels") else ""
            checks = ""
            if t.get("checklist_items"):
                done = sum(1 for c in t["checklist_items"] if c["complete"])
                total = len(t["checklist_items"])
                checks = f" ({done}/{total} done)"
            lines.append(f"    - {t['name']}{labels}{checks}")
            if t.get("description"):
                lines.append(f"      └ {t['description'][:100]}")
    return "\n".join(lines)


def _format_emails(emails: list[dict]) -> str:
    if not emails:
        return "  Inbox clear — no unread/important emails."
    lines = []
    for e in emails[:10]:
        lines.append(f"  - From: {e['sender']}")
        lines.append(f"    Subject: {e['subject']}")
        lines.append(f"    Preview: {e['snippet'][:120]}")
        lines.append("")
    return "\n".join(lines)


def _format_plaud(notes: list[dict]) -> str:
    if not notes:
        return "  No recent Plaud recordings."
    lines = []
    for n in notes:
        lines.append(f"  - {n.get('title', 'Untitled')} ({n.get('date', 'Unknown date')})")
        if n.get("summary"):
            lines.append(f"    Summary: {n['summary'][:200]}")
        lines.append("")
    return "\n".join(lines)
