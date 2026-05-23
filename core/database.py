"""
LagroEyewear Database Module
============================

SQLite database operations for persisting session data, blink events,
and break events. Provides thread-safe access to all tracking data
used by the application's analytics and history features.
"""

import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional


class Database:
    """Manages all SQLite database operations for LagroEyewear.

    Handles creation and management of sessions, blink events, and break events.
    Uses check_same_thread=False for thread-safe access from multiple threads.

    Attributes:
        db_path: Path to the SQLite database file.
        conn: Active SQLite connection.
        cursor: Active SQLite cursor.
    """

    def __init__(self, db_path: str) -> None:
        """Initialize the database connection and ensure tables exist.

        Args:
            db_path: Filesystem path to the SQLite database file.
                     Will be created if it does not exist.
        """
        self.db_path: str = db_path
        self.conn: sqlite3.Connection = sqlite3.connect(
            db_path, check_same_thread=False
        )
        self.conn.row_factory = sqlite3.Row  # Enable dict-like row access
        self.cursor: sqlite3.Cursor = self.conn.cursor()
        self.init_db()

    def init_db(self) -> None:
        """Create all required tables if they do not already exist.

        Tables:
            - sessions: Stores high-level session data (start/end times, averages).
            - blink_events: Per-interval blink rate and EAR snapshots.
            - break_events: Records of each break taken or dismissed.
        """
        self.cursor.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time        DATETIME NOT NULL,
                end_time          DATETIME,
                avg_blink_rate    REAL,
                total_blinks      INTEGER,
                breaks_taken      INTEGER,
                eye_strain_score  REAL
            );

            CREATE TABLE IF NOT EXISTS blink_events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  INTEGER NOT NULL,
                timestamp   DATETIME NOT NULL,
                blink_rate  REAL,
                ear_value   REAL,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );

            CREATE TABLE IF NOT EXISTS break_events (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id       INTEGER NOT NULL,
                timestamp        DATETIME NOT NULL,
                trigger_type     TEXT,
                duration_seconds INTEGER,
                dismissed_early  BOOLEAN,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );
        """)
        self.conn.commit()

    def create_session(self) -> int:
        """Create a new tracking session.

        Returns:
            The auto-generated session ID for the new session.
        """
        now: str = datetime.now().isoformat()
        self.cursor.execute(
            "INSERT INTO sessions (start_time) VALUES (?)",
            (now,)
        )
        self.conn.commit()
        return self.cursor.lastrowid  # type: ignore[return-value]

    def end_session(
        self,
        session_id: int,
        avg_blink_rate: float,
        total_blinks: int,
        breaks_taken: int,
        eye_strain_score: float,
    ) -> None:
        """Finalize a session with computed statistics.

        Args:
            session_id: The ID of the session to close.
            avg_blink_rate: Average blinks per minute over the session.
            total_blinks: Total number of blinks detected.
            breaks_taken: Number of breaks taken during the session.
            eye_strain_score: Final eye strain score (0–100).
        """
        now: str = datetime.now().isoformat()
        self.cursor.execute(
            """UPDATE sessions
               SET end_time = ?, avg_blink_rate = ?, total_blinks = ?,
                   breaks_taken = ?, eye_strain_score = ?
               WHERE id = ?""",
            (now, avg_blink_rate, total_blinks, breaks_taken, eye_strain_score, session_id),
        )
        self.conn.commit()

    def log_blink_event(
        self,
        session_id: int,
        blink_rate: float,
        ear_value: float,
    ) -> None:
        """Record a blink rate snapshot for a session.

        Args:
            session_id: The session this event belongs to.
            blink_rate: Current blinks-per-minute reading.
            ear_value: Current Eye Aspect Ratio value.
        """
        now: str = datetime.now().isoformat()
        self.cursor.execute(
            """INSERT INTO blink_events (session_id, timestamp, blink_rate, ear_value)
               VALUES (?, ?, ?, ?)""",
            (session_id, now, blink_rate, ear_value),
        )
        self.conn.commit()

    def log_break_event(
        self,
        session_id: int,
        trigger_type: str,
        duration_seconds: int,
        dismissed_early: bool,
    ) -> None:
        """Record a break event for a session.

        Args:
            session_id: The session this break belongs to.
            trigger_type: How the break was triggered ('scheduled' or 'emergency').
            duration_seconds: How many seconds the break lasted.
            dismissed_early: Whether the user dismissed the break before completion.
        """
        now: str = datetime.now().isoformat()
        self.cursor.execute(
            """INSERT INTO break_events
               (session_id, timestamp, trigger_type, duration_seconds, dismissed_early)
               VALUES (?, ?, ?, ?, ?)""",
            (session_id, now, trigger_type, duration_seconds, dismissed_early),
        )
        self.conn.commit()

    def get_session_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve the most recent sessions.

        Args:
            limit: Maximum number of sessions to return (default 10).

        Returns:
            List of session dictionaries ordered by start_time descending.
        """
        self.cursor.execute(
            "SELECT * FROM sessions ORDER BY start_time DESC LIMIT ?",
            (limit,),
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def get_blink_events(
        self,
        session_id: int,
        minutes: int = 10,
    ) -> List[Dict[str, Any]]:
        """Retrieve recent blink events for a session (used for charting).

        Args:
            session_id: The session to query.
            minutes: How many minutes of history to fetch (default 10).

        Returns:
            List of blink event dictionaries ordered by timestamp ascending.
        """
        self.cursor.execute(
            """SELECT * FROM blink_events
               WHERE session_id = ?
                 AND timestamp >= datetime('now', ?)
               ORDER BY timestamp ASC""",
            (session_id, f"-{minutes} minutes"),
        )
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def close(self) -> None:
        """Close the database connection gracefully."""
        try:
            self.conn.close()
        except Exception:
            pass  # Silently handle already-closed connections
