import json
import os
import sqlite3
from datetime import date

DB_PATH = os.environ.get("BRIEFING_DB_PATH", "briefings.db")


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS briefings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brief_date DATE NOT NULL UNIQUE,
            sections_json TEXT NOT NULL,
            raw_markdown TEXT,
            generated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    db.commit()
    return db


def save_briefing(brief_date: date, sections: dict, raw_markdown: str):
    db = sqlite3.connect(DB_PATH)
    db.execute(
        "INSERT OR REPLACE INTO briefings (brief_date, sections_json, raw_markdown) VALUES (?, ?, ?)",
        (brief_date.isoformat(), json.dumps(sections), raw_markdown),
    )
    db.commit()
    db.close()


def get_latest() -> dict | None:
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    row = db.execute("SELECT * FROM briefings ORDER BY brief_date DESC LIMIT 1").fetchone()
    db.close()
    if not row:
        return None
    return {
        "date": row["brief_date"],
        "sections": json.loads(row["sections_json"]),
        "raw_markdown": row["raw_markdown"],
        "generated_at": row["generated_at"],
    }


def get_by_date(d: str) -> dict | None:
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    row = db.execute("SELECT * FROM briefings WHERE brief_date = ?", (d,)).fetchone()
    db.close()
    if not row:
        return None
    return {
        "date": row["brief_date"],
        "sections": json.loads(row["sections_json"]),
        "raw_markdown": row["raw_markdown"],
        "generated_at": row["generated_at"],
    }
