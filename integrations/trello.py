"""
Trello integration — fetches tasks from today's column.
Uses Trello REST API directly (py-trello was getting CloudFront 403s).
Board structure: each list (column) = a day of the week.
Columns named: ★MONDAY★, ★TUESDAY★, etc.
Cards use colored header cards (KJD, CRTVS, ALP, PERSO) as category separators.
"""

import os
import datetime
import requests


TRELLO_API_BASE = "https://api.trello.com/1"

# Davo's column names use star emoji wrappers
DAY_KEYWORDS = {
    0: "monday",
    1: "tuesday",
    2: "wednesday",
    3: "thursday",
    4: "friday",
    5: "saturday",
    6: "sunday",
}

# These are category header cards, not actual tasks.
CATEGORY_HEADERS = {"kjd", "crtvs", "alp", "perso", "sales"}


def _trello_params():
    """Return auth params for Trello API."""
    return {
        "key": os.getenv("TRELLO_API_KEY"),
        "token": os.getenv("TRELLO_TOKEN"),
    }


def _trello_get(endpoint: str, extra_params: dict = None) -> dict | list:
    """Make a GET request to Trello API with proper headers."""
    params = _trello_params()
    if extra_params:
        params.update(extra_params)

    headers = {
        "Accept": "application/json",
        "User-Agent": "DavoBriefingAgent/1.0 (+https://kojador.com)",
    }

    resp = requests.get(
        f"{TRELLO_API_BASE}{endpoint}",
        params=params,
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _is_header_card(card_name: str) -> bool:
    """Check if a card is just a category header (KJD, CRTVS, ALP, PERSO, etc.)."""
    stripped = card_name.strip().lower()
    return stripped in CATEGORY_HEADERS


def _get_category(card_name: str, current_category: str) -> str:
    """If this card is a header, return the new category. Otherwise return current."""
    stripped = card_name.strip().lower()
    if stripped in CATEGORY_HEADERS:
        category_map = {
            "kjd": "Koja d'Or",
            "crtvs": "Creatives",
            "alp": "ALP",
            "perso": "Personal",
            "sales": "Sales",
        }
        return category_map.get(stripped, stripped.upper())
    return current_category


def fetch_trello_tasks(target_date: datetime.date = None) -> list[dict]:
    """
    Fetch all cards from the list matching target_date's day name.
    Groups tasks by category (KJD, CRTVS, ALP, PERSO).
    Returns list of dicts: name, category, description, due, labels, checklist_items.
    """
    if target_date is None:
        target_date = datetime.date.today()

    day_keyword = DAY_KEYWORDS[target_date.weekday()]
    board_id = os.getenv("TRELLO_BOARD_ID")

    # 1. Get all lists on the board
    lists = _trello_get(f"/boards/{board_id}/lists", {"filter": "open"})

    # 2. Find the list matching tomorrow's day
    target_list_id = None
    for lst in lists:
        cleaned_name = lst["name"].strip().lower().replace("★", "").replace("*", "").strip()
        if day_keyword in cleaned_name:
            target_list_id = lst["id"]
            break

    if target_list_id is None:
        return [{"name": f"No Trello list found for {day_keyword.title()}", "description": "", "category": "Unknown"}]

    # 3. Get all cards in that list
    cards = _trello_get(
        f"/lists/{target_list_id}/cards",
        {"fields": "name,desc,due,labels", "checklists": "all"},
    )

    parsed = []
    current_category = "Uncategorized"

    for card in cards:
        card_name = card.get("name", "")

        # Check if this is a category header card
        if _is_header_card(card_name):
            current_category = _get_category(card_name, current_category)
            continue  # Skip header cards — they're not tasks

        # Pull checklist items if any
        checklist_items = []
        for cl in card.get("checklists", []):
            for item in cl.get("checkItems", []):
                checklist_items.append({
                    "text": item.get("name", ""),
                    "complete": item.get("state") == "complete",
                })

        # Labels
        label_names = [l.get("name", "") for l in card.get("labels", []) if l.get("name")]

        parsed.append({
            "name": card_name,
            "category": current_category,
            "description": card.get("desc", ""),
            "due": card.get("due"),
            "labels": label_names,
            "checklist_items": checklist_items,
        })

    return parsed
