"""
Davo's recurring schedule constraints.
These are hard-blocked time slots that the briefing accounts for.
"""

from datetime import date, time, timedelta


def is_arlo_day(target_date: date) -> bool:
    """
    Determine if target_date is an Arlo day.
    Every other day — pure alternation, no day-of-week exceptions.
    Reference: Friday March 27, 2026 is a confirmed Arlo day.
    Pattern: Fri 27 → Sun 29 → Tue 31 → Thu Apr 2 → Sat Apr 4 → ...
    """
    import os
    ref_str = os.getenv("ARLO_REFERENCE_DATE", "2026-03-27")
    ref_date = date.fromisoformat(ref_str)

    delta = (target_date - ref_date).days
    return delta % 2 == 0


def is_lily_friday(target_date: date) -> bool:
    """On Friday Arlo days, Lily handles dropoff/pickup — Davo is free of logistics."""
    return target_date.weekday() == 4 and is_arlo_day(target_date)


def get_fixed_blocks(target_date: date) -> list[dict]:
    """
    Return Davo's non-negotiable time blocks for the given date.
    These are placed into the briefing so the AI can plan around them.
    """
    blocks = []
    arlo_day = is_arlo_day(target_date)
    lily_friday = is_lily_friday(target_date)

    # --- Morning ---
    if arlo_day and not lily_friday:
        # Normal Arlo day — Davo does dropoff then dog walk
        blocks.append({
            "time": "08:00 – 08:30",
            "activity": "Drop off Arlo",
            "type": "personal",
            "priority": "non-negotiable",
        })
        blocks.append({
            "time": "08:30 – 09:00",
            "activity": "Morning dog walk",
            "type": "personal",
            "priority": "non-negotiable",
        })
    else:
        # Non-Arlo day or Lily Friday — just dog walk
        blocks.append({
            "time": "08:00 – 08:30",
            "activity": "Morning dog walk",
            "type": "personal",
            "priority": "non-negotiable",
        })

    # --- Lunch ---
    blocks.append({
        "time": "12:00 – 12:30",
        "activity": "Lunch dog walk",
        "type": "personal",
        "priority": "non-negotiable",
    })

    # --- Afternoon ---
    blocks.append({
        "time": "15:00 – 15:20",
        "activity": "Afternoon dog walk",
        "type": "personal",
        "priority": "non-negotiable",
    })

    # --- Evening ---
    if arlo_day and not lily_friday:
        # Normal Arlo day — Davo does pickup
        blocks.append({
            "time": "17:30",
            "activity": "Pick up Arlo",
            "type": "personal",
            "priority": "non-negotiable",
        })

    if lily_friday:
        blocks.append({
            "time": "All day",
            "activity": "Arlo day — Lily handling dropoff/pickup today",
            "type": "info",
            "priority": "note",
        })

    return blocks


def format_blocks_for_prompt(blocks: list[dict]) -> str:
    """Format the fixed blocks as readable text for the AI prompt."""
    lines = []
    for b in blocks:
        marker = "🔒" if b["priority"] == "non-negotiable" else "ℹ️"
        lines.append(f"  {marker} {b['time']} — {b['activity']}")
    return "\n".join(lines)
