"""
Trello integration — fetches tasks from tomorrow's column.
Board structure: each list (column) = a day of the week.
Columns named: ★MONDAY★, ★TUESDAY★, etc.
Cards use colored header cards (KJD, CRTVS, ALP, PERSO) as category separators.
"""

import os
import datetime
from trello import TrelloClient


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
# They separate tasks by business/personal context.
CATEGORY_HEADERS = {"kjd", "crtvs", "alp", "perso", "sales"}


def get_client():
    return TrelloClient(
        api_key=os.getenv("TRELLO_API_KEY"),
        token=os.getenv("TRELLO_TOKEN"),
    )


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
        target_date = datetime.date.today() + datetime.timedelta(days=1)

    day_keyword = DAY_KEYWORDS[target_date.weekday()]
    client = get_client()
    board_id = os.getenv("TRELLO_BOARD_ID")
    board = client.get_board(board_id)

    # Find the list — match day keyword inside column name
    # Handles: ★MONDAY★, ★ MONDAY ★, Monday, etc.
    target_list = None
    for lst in board.list_lists():
        cleaned_name = lst.name.strip().lower().replace("★", "").replace("*", "").strip()
        if day_keyword in cleaned_name:
            target_list = lst
            break

    if target_list is None:
        return [{"name": f"No Trello list found for {day_keyword.title()}", "description": "", "category": "Unknown"}]

    cards = target_list.list_cards()
    parsed = []
    current_category = "Uncategorized"

    for card in cards:
        # Check if this is a category header card
        if _is_header_card(card.name):
            current_category = _get_category(card.name, current_category)
            continue  # Skip header cards — they're not tasks

        # Pull checklist items if any
        checklist_items = []
        for cl in card.fetch_checklists():
            for item in cl.items:
                checklist_items.append({
                    "text": item["name"],
                    "complete": item["checked"],
                })

        # Check for priority/status labels
        label_names = [l.name for l in card.labels] if card.labels else []

        parsed.append({
            "name": card.name,
            "category": current_category,
            "description": card.description or "",
            "due": str(card.due_date) if card.due_date else None,
            "labels": label_names,
            "checklist_items": checklist_items,
        })

    return parsed
