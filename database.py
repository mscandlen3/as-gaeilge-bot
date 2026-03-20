import sqlite3
import json
from datetime import datetime

DB_PATH = "irish_bot.db"


def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER PRIMARY KEY,
            username    TEXT,
            joined_at   TEXT,
            current_unit INTEGER DEFAULT 1
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            unit        INTEGER,
            completed_at TEXT,
            score       INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            role        TEXT,
            content     TEXT,
            timestamp   TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pronunciation_attempts (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER,
            target_text   TEXT,
            transcription TEXT,
            score         TEXT,
            attempted_at  TEXT
        )
    """)

    con.commit()
    con.close()


# ── User ──────────────────────────────────────────────────────────────────────

def upsert_user(user_id: int, username: str):
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        INSERT INTO users (user_id, username, joined_at, current_unit)
        VALUES (?, ?, ?, 1)
        ON CONFLICT(user_id) DO UPDATE SET username=excluded.username
    """, (user_id, username, datetime.utcnow().isoformat()))
    con.commit()
    con.close()


def get_current_unit(user_id: int) -> int:
    con = sqlite3.connect(DB_PATH)
    row = con.execute("SELECT current_unit FROM users WHERE user_id=?", (user_id,)).fetchone()
    con.close()
    return row[0] if row else 1


def set_current_unit(user_id: int, unit: int):
    con = sqlite3.connect(DB_PATH)
    con.execute("UPDATE users SET current_unit=? WHERE user_id=?", (unit, user_id))
    con.commit()
    con.close()


# ── Progress ──────────────────────────────────────────────────────────────────

def mark_unit_complete(user_id: int, unit: int, score: int | None = None):
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        INSERT INTO progress (user_id, unit, completed_at, score)
        VALUES (?, ?, ?, ?)
    """, (user_id, unit, datetime.utcnow().isoformat(), score))
    con.commit()
    con.close()


def get_progress(user_id: int) -> list[dict]:
    con = sqlite3.connect(DB_PATH)
    rows = con.execute("""
        SELECT unit, completed_at, score FROM progress
        WHERE user_id=? ORDER BY completed_at
    """, (user_id,)).fetchall()
    con.close()
    return [{"unit": r[0], "completed_at": r[1], "score": r[2]} for r in rows]


def get_completed_units(user_id: int) -> set[int]:
    return {r["unit"] for r in get_progress(user_id)}


# ── History ───────────────────────────────────────────────────────────────────

def save_message(user_id: int, role: str, content: str):
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        INSERT INTO history (user_id, role, content, timestamp)
        VALUES (?, ?, ?, ?)
    """, (user_id, role, content, datetime.utcnow().isoformat()))
    con.commit()
    con.close()


def load_history(user_id: int, limit: int = 20) -> list[dict]:
    con = sqlite3.connect(DB_PATH)
    rows = con.execute("""
        SELECT role, content FROM history
        WHERE user_id=? ORDER BY id DESC LIMIT ?
    """, (user_id, limit)).fetchall()
    con.close()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]


# ── Pronunciation ─────────────────────────────────────────────────────────────

def save_pronunciation_attempt(user_id: int, target: str, transcription: str, score: str):
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        INSERT INTO pronunciation_attempts (user_id, target_text, transcription, score, attempted_at)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, target, transcription, score, datetime.utcnow().isoformat()))
    con.commit()
    con.close()


def get_pronunciation_stats(user_id: int) -> dict:
    con = sqlite3.connect(DB_PATH)
    rows = con.execute("""
        SELECT score, COUNT(*) FROM pronunciation_attempts
        WHERE user_id=? GROUP BY score
    """, (user_id,)).fetchall()
    con.close()
    return {r[0]: r[1] for r in rows}
