"""
LagroEyewear Session Manager Module
====================================

Manages eye-tracking sessions, computes eye strain scores, and determines
when the user should take a break (both scheduled and emergency).
Acts as the bridge between the BlinkDetector, Database, and the UI.
"""

import time
from datetime import timedelta
from typing import Optional, Tuple

from core.database import Database
from utils.settings import Settings


class SessionManager:
    """Tracks a single monitoring session and its metrics.

    Coordinates blink event logging, eye strain scoring, and break
    scheduling based on user-configurable settings.

    Attributes:
        db: Database instance for persistence.
        settings: Settings instance for user preferences.
    """

    def __init__(self, database: Database, settings: Settings) -> None:
        """Initialise the session manager.

        Args:
            database: Database instance for persisting session data.
            settings: Settings instance for retrieving user preferences.
        """
        self.db: Database = database
        self.settings: Settings = settings

        # ── Session state ─────────────────────────────────────────────────
        self._session_id: Optional[int] = None
        self._session_start: Optional[float] = None
        self._paused: bool = False
        self._pause_start: Optional[float] = None
        self._total_paused_seconds: float = 0.0

        # ── Tracking variables ────────────────────────────────────────────
        self._blink_rates: list[float] = []        # All recorded blink rates
        self._low_blink_start: Optional[float] = None  # When low-blink streak began
        self._breaks_taken: int = 0
        self._completed_breaks: int = 0  # Breaks NOT dismissed early
        self._last_break_time: Optional[float] = None
        self._total_blinks_snapshot: int = 0

    # ─── Session lifecycle ────────────────────────────────────────────────

    def start_session(self) -> int:
        """Create a new session in the database and initialise tracking.

        Returns:
            The new session ID.
        """
        self._session_id = self.db.create_session()
        self._session_start = time.time()
        self._paused = False
        self._pause_start = None
        self._total_paused_seconds = 0.0

        # Reset tracking vars
        self._blink_rates = []
        self._low_blink_start = None
        self._breaks_taken = 0
        self._completed_breaks = 0
        self._last_break_time = time.time()
        self._total_blinks_snapshot = 0

        return self._session_id

    def end_session(self) -> None:
        """Finalize the current session with computed statistics."""
        if self._session_id is None:
            return

        # Compute averages
        avg_blink_rate = 0.0
        if self._blink_rates:
            avg_blink_rate = sum(self._blink_rates) / len(self._blink_rates)

        strain_score = self.calculate_eye_strain_score()

        self.db.end_session(
            session_id=self._session_id,
            avg_blink_rate=round(avg_blink_rate, 2),
            total_blinks=self._total_blinks_snapshot,
            breaks_taken=self._breaks_taken,
            eye_strain_score=round(strain_score, 2),
        )

        self._session_id = None
        self._session_start = None

    # ─── Periodic update (called by UI timer) ─────────────────────────────

    def update(self, blink_rate: float, ear_value: float) -> None:
        """Process a periodic update with current blink rate and EAR.

        Called at regular intervals by the UI to log data, update
        the strain score, and check break conditions.

        Args:
            blink_rate: Current blinks-per-minute reading.
            ear_value: Current Eye Aspect Ratio value.
        """
        if self._session_id is None or self._paused:
            return

        # Log to database
        self.db.log_blink_event(self._session_id, blink_rate, ear_value)

        # Track blink rates for averages
        self._blink_rates.append(blink_rate)

        # Track low-blink streaks for emergency breaks
        low_threshold: float = self.settings.get("low_blink_threshold")
        if blink_rate < low_threshold:
            if self._low_blink_start is None:
                self._low_blink_start = time.time()
        else:
            self._low_blink_start = None

    def update_total_blinks(self, total_blinks: int) -> None:
        """Update the running total blink count from the detector.

        Args:
            total_blinks: Current total blink count from BlinkDetector.
        """
        self._total_blinks_snapshot = total_blinks

    # ─── Eye strain scoring ───────────────────────────────────────────────

    def calculate_eye_strain_score(self) -> int:
        """Compute an eye strain score from 0 (worst) to 100 (best).

        Scoring rules:
            - Start at 100
            - Subtract 2 for every minute blink rate was below 12
            - Subtract 1 for every 10 minutes without a break
            - Add 5 for each fully completed break
            - Clamp to [0, 100]

        Returns:
            Eye strain score as an integer (0–100).
        """
        score: float = 100.0

        # Penalty: low blink rate minutes
        low_threshold: float = self.settings.get("low_blink_threshold")
        low_blink_minutes = sum(1 for r in self._blink_rates if r < low_threshold)
        score -= low_blink_minutes * 2

        # Penalty: time without breaks (in 10-minute chunks)
        session_elapsed = self.get_session_time().total_seconds()
        if session_elapsed > 0:
            # Minutes without any break, in 10-min blocks
            minutes_without_break = session_elapsed / 60.0
            if self._breaks_taken > 0:
                avg_gap = minutes_without_break / self._breaks_taken
                penalty_blocks = int(avg_gap / 10)
            else:
                penalty_blocks = int(minutes_without_break / 10)
            score -= penalty_blocks * 1

        # Bonus: completed breaks
        score += self._completed_breaks * 5

        # Clamp to [0, 100]
        return int(max(0, min(100, score)))

    # ─── Break management ─────────────────────────────────────────────────

    def should_trigger_break(self) -> Tuple[bool, str]:
        """Determine whether the user should take a break.

        Returns:
            A tuple of (should_break, reason) where reason is one of:
            - 'scheduled': Regular interval break.
            - 'emergency': Blink rate has been critically low for > 60s.
            - '': No break needed.
        """
        if self._session_id is None or self._paused:
            return (False, "")

        now = time.time()

        # ── Emergency break: low blink rate for > 60 seconds ─────────────
        if self._low_blink_start is not None:
            low_duration = now - self._low_blink_start
            if low_duration > 60.0:
                return (True, "emergency")

        # ── Scheduled break: time since last break > interval ────────────
        break_interval_sec = self.settings.get("break_interval") * 60  # minutes → seconds
        if self._last_break_time is not None:
            elapsed_since_break = now - self._last_break_time
            if elapsed_since_break >= break_interval_sec:
                return (True, "scheduled")

        return (False, "")

    def record_break(
        self,
        trigger_type: str,
        duration: int,
        dismissed_early: bool,
    ) -> None:
        """Record that a break was taken.

        Args:
            trigger_type: 'scheduled' or 'emergency'.
            duration: Duration of the break in seconds.
            dismissed_early: Whether the user ended the break early.
        """
        if self._session_id is None:
            return

        self.db.log_break_event(
            session_id=self._session_id,
            trigger_type=trigger_type,
            duration_seconds=duration,
            dismissed_early=dismissed_early,
        )

        self._breaks_taken += 1
        if not dismissed_early:
            self._completed_breaks += 1

        self._last_break_time = time.time()
        self._low_blink_start = None  # Reset low-blink streak after break

    # ─── Session info getters ─────────────────────────────────────────────

    def get_session_time(self) -> timedelta:
        """Get the total active session duration (excluding paused time).

        Returns:
            A timedelta representing the active session time.
        """
        if self._session_start is None:
            return timedelta(0)

        elapsed = time.time() - self._session_start - self._total_paused_seconds

        # If currently paused, subtract ongoing pause time
        if self._paused and self._pause_start is not None:
            elapsed -= (time.time() - self._pause_start)

        return timedelta(seconds=max(0, elapsed))

    def get_breaks_taken(self) -> int:
        """Get the number of breaks taken in this session.

        Returns:
            Total break count (int).
        """
        return self._breaks_taken

    def get_time_until_break(self) -> float:
        """Get the number of seconds remaining until the next scheduled break.

        Returns:
            Seconds until next break (float). Returns 0 if overdue.
        """
        if self._last_break_time is None:
            return 0.0

        break_interval_sec = self.settings.get("break_interval") * 60
        elapsed = time.time() - self._last_break_time
        remaining = break_interval_sec - elapsed

        return max(0.0, remaining)

    # ─── Pause / Resume ──────────────────────────────────────────────────

    def pause(self) -> None:
        """Pause session tracking."""
        if not self._paused:
            self._paused = True
            self._pause_start = time.time()

    def resume(self) -> None:
        """Resume session tracking after a pause."""
        if self._paused and self._pause_start is not None:
            self._total_paused_seconds += time.time() - self._pause_start
            self._paused = False
            self._pause_start = None

    def is_paused(self) -> bool:
        """Check whether the session is currently paused.

        Returns:
            True if tracking is paused.
        """
        return self._paused

    @property
    def session_id(self) -> Optional[int]:
        """The current session ID, or None if no session is active."""
        return self._session_id
