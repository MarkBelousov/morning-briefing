import sqlite3
import os
import uuid
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "subscribers.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            phone TEXT,
            carrier TEXT,
            confirmed INTEGER DEFAULT 1,
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            unsubscribe_token TEXT UNIQUE
        )
    """)
    conn.commit()
    conn.close()


def add_subscriber(email, phone="", carrier=""):
    conn = get_conn()
    token = str(uuid.uuid4())
    try:
        conn.execute(
            "INSERT OR IGNORE INTO subscribers (email, phone, carrier, unsubscribe_token) VALUES (?, ?, ?, ?)",
            (email, phone, carrier, token),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM subscribers WHERE email = ?", (email,)
        ).fetchone()
        conn.close()
        return row
    except Exception as e:
        conn.close()
        return None


def remove_subscriber(token):
    conn = get_conn()
    conn.execute("UPDATE subscribers SET active = 0 WHERE unsubscribe_token = ?", (token,))
    conn.commit()
    conn.close()


def get_active_subscribers():
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM subscribers WHERE active = 1 AND confirmed = 1"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_subscriber_by_token(token):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM subscribers WHERE unsubscribe_token = ?", (token,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def subscriber_count():
    conn = get_conn()
    count = conn.execute(
        "SELECT COUNT(*) FROM subscribers WHERE active = 1 AND confirmed = 1"
    ).fetchone()[0]
    conn.close()
    return count
