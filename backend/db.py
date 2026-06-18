"""
db.py — SQLite database layer using Python's built-in sqlite3 module.

Exposes a simple interface for executing queries. The database is stored
at backend/medirush.db — a standard SQLite file that any SQLite client
(e.g. DB Browser for SQLite) can open.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'medirush.db')

SCHEMA = """
    CREATE TABLE IF NOT EXISTS users (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        email           TEXT UNIQUE NOT NULL,
        password_hash   TEXT NOT NULL,
        full_name       TEXT,
        phone           TEXT,
        email_verified  INTEGER DEFAULT 0,
        created_at      TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS user_medical (
        user_id                 INTEGER PRIMARY KEY REFERENCES users(id),
        blood_type              TEXT,
        allergies               TEXT,
        medications             TEXT,
        conditions              TEXT,
        emergency_contact_name  TEXT,
        emergency_contact_phone TEXT
    );

    CREATE TABLE IF NOT EXISTS otps (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        email       TEXT NOT NULL,
        otp         TEXT NOT NULL,
        expires_at  TEXT NOT NULL,
        used        INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS bookings (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id        INTEGER NOT NULL REFERENCES users(id),
        request_id     TEXT UNIQUE NOT NULL,
        patient_name   TEXT,
        patient_phone  TEXT,
        location       TEXT,
        emergency_type TEXT,
        ambulance_type TEXT,
        severity_level INTEGER,
        severity_word  TEXT,
        description    TEXT,
        eta_minutes    INTEGER,
        unit_assigned  TEXT,
        status         TEXT DEFAULT 'dispatched',
        created_at     TEXT DEFAULT (datetime('now'))
    );
"""


def get_connection():
    """Open and return a new SQLite connection with row_factory set."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def query_one(sql, params=()):
    """Execute a SELECT and return the first row as a dict, or None."""
    with get_connection() as conn:
        row = conn.execute(sql, params).fetchone()
    return dict(row) if row else None


def query_all(sql, params=()):
    """Execute a SELECT and return all rows as a list of dicts."""
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def execute(sql, params=()):
    """Execute an INSERT / UPDATE / DELETE and return rowcount."""
    with get_connection() as conn:
        cursor = conn.execute(sql, params)
        conn.commit()
        return cursor.rowcount


def init():
    """Create the schema (idempotent). Call once at startup."""
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        conn.commit()
    print(f'Database ready -> {DB_PATH}')
