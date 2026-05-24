import sqlite3
import json
from datetime import datetime

DB_PATH = "leads.db"


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id TEXT PRIMARY KEY,
                sender_id       TEXT,
                sender_name     TEXT,
                platform        TEXT DEFAULT 'instagram',
                stage           TEXT DEFAULT 'active',
                messages        TEXT DEFAULT '[]',
                lead_data       TEXT DEFAULT '{}',
                created_at      TEXT,
                updated_at      TEXT
            )
        """)
        conn.commit()


def get_conversation(conversation_id: str) -> dict | None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM conversations WHERE conversation_id = ?",
            (conversation_id,),
        ).fetchone()
    if not row:
        return None
    data = dict(row)
    data["messages"] = json.loads(data["messages"])
    data["lead_data"] = json.loads(data["lead_data"])
    return data


def upsert_conversation(
    conversation_id: str,
    sender_id: str = "",
    sender_name: str = "",
    platform: str = "instagram",
    messages: list = None,
    lead_data: dict = None,
    stage: str = "active",
) -> None:
    now = datetime.utcnow().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO conversations
                (conversation_id, sender_id, sender_name, platform,
                 messages, lead_data, stage, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(conversation_id) DO UPDATE SET
                messages   = excluded.messages,
                lead_data  = excluded.lead_data,
                stage      = excluded.stage,
                updated_at = excluded.updated_at
            """,
            (
                conversation_id,
                sender_id,
                sender_name,
                platform,
                json.dumps(messages or []),
                json.dumps(lead_data or {}),
                stage,
                now,
                now,
            ),
        )
        conn.commit()


def get_all_qualified_leads() -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM conversations WHERE stage = 'qualified' ORDER BY updated_at DESC"
        ).fetchall()
    result = []
    for row in rows:
        data = dict(row)
        data["messages"] = json.loads(data["messages"])
        data["lead_data"] = json.loads(data["lead_data"])
        result.append(data)
    return result
