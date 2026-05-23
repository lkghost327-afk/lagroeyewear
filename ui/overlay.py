"""
LagroEyewear Break Overlay Module.

Provides a fullscreen overlay that encourages the user to rest their eyes.
Displays a countdown timer, pulsing eye icon, and progress bar.
"""

from __future__ import annotations

import math
from typing import Any, Callable, Optional

import customtkinter as ctk

# ── Color Palette ──────────────────────────────────────────────────────────────
BG = '#0D1117'
CARD_BG = '#161B22'
ACCENT = '#4A90FF'
GREEN = '#00E5A0'
AMBER = '#FFB800'
RED = '#FF4D4D'
TEXT = '#E6EDF3'
TEXT_SEC = '#8B949E'


class BreakOverlay:
    """Fullscreen break overlay that guides the user through a 20-20-20 rest.

    Creates a :class:`ctk.CTkToplevel` covering the entire screen with a
    semi-transparent dark background, centred countdown timer, progress bar,
    and a pulsing eye icon animation.

    Args:
        master: The parent widget (usually the main ``CTk`` window).
    """

    def __init__(self, master: Any) -> None:
        self._master = master
        self._window: Optional[ctk.CTkToplevel] = None
        self._on_complete: Optional[Callable[[], None]] = None
        self._on_dismiss: Optional[Callable[[], None]] = None

        # Countdown state
        self._remaining_ms: int = 0
        self._total_ms: int = 0
        self._timer_id: Optional[str] = None

        # Pulse animation state
        self._pulse_phase: float = 0.0
        self._pulse_id: Optional[str] = None

    # ═══════════════════════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════════════════════

    def show(
        self,
        duration: int = 20,
        on_complete: Optional[Callable[[], None]] = None,
        on_dismiss: Optional[Callable[[], None]] = None,
    ) -> None:
        """Show the break overlay and start the countdown.

        Args:
            duration: Break duration in seconds (default ``20``).
            on_complete: Called when the countdown naturally reaches zero.
            on_dismiss: Called when the user presses ESC to dismiss early.
        """
        self._on_complete = on_complete
        self._on_dismiss = on_dismiss
        self._total_ms = duration * 1000
        self._remaining_ms = self._total_ms

        self._build_window()
        self._start_countdown()
        self._start_pulse()

    def dismiss(self) -> None:
        """Dismiss the overlay early (e.g. user pressed ESC)."""
        self._stop_timers()
        if self._window is not None and self._window.winfo_exists():
            self._window.destroy()
            self._window = None
        if self._on_dismiss is not None:
            try:
                self._on_dismiss()
            except Exception:
                pass

    # ═══════════════════════════════════════════════════════════════════════
    # Window construction
    # ═══════════════════════════════════════════════════════════════════════

    def _build_window(self) -> None:
        """Create the fullscreen overlay window and all child widgets."""
        # Destroy any previous overlay
        if self._window is not None and self._window.winfo_exists():
            self._window.destroy()

        win = ctk.CTkToplevel(self._master)
        win.title('')
        win.configure(fg_color=BG)

        # Fullscreen, borderless, always on top
        win.overrideredirect(True)
        win.attributes('-topmost', True)

        # Semi-transparent
        try:
            win.wm_attributes('-alpha', 0.92)
        except Exception:
            pass  # Transparency not supported on all platforms

        # Cover entire screen
        screen_w = win.winfo_screenwidth()
        screen_h = win.winfo_screenheight()
        win.geometry(f'{screen_w}x{screen_h}+0+0')

        # Bind ESC to dismiss
        win.bind('<Escape>', lambda _e: self.dismiss())

        # ── Centre container ───────────────────────────────────────────────
        container = ctk.CTkFrame(win, fg_color='transparent')
        container.place(relx=0.5, rely=0.5, anchor='center')

        # Eye icon (pulsing)
        self._eye_label = ctk.CTkLabel(
            container,
            text='👁️',
            text_color=TEXT,
            font=ctk.CTkFont(size=60),
        )
        self._eye_label.pack(pady=(0, 16))

        # Title
        ctk.CTkLabel(
            container,
            text='Rest Your Eyes',
            text_color='#FFFFFF',
            font=ctk.CTkFont(size=36, weight='bold'),
        ).pack(pady=(0, 8))

        # Subtitle
        ctk.CTkLabel(
            container,
            text='Look 20 feet away for 20 seconds.',
            text_color=TEXT_SEC,
            font=ctk.CTkFont(size=18),
        ).pack(pady=(0, 28))

        # Countdown number
        self._countdown_label = ctk.CTkLabel(
            container,
            text=str(self._remaining_ms // 1000),
            text_color=ACCENT,
            font=ctk.CTkFont(size=72, weight='bold'),
        )
        self._countdown_label.pack(pady=(0, 24))

        # Progress bar
        self._progress = ctk.CTkProgressBar(
            container,
            width=360,
            height=6,
            corner_radius=3,
            fg_color='#21262D',
            progress_color=ACCENT,
        )
        self._progress.set(1.0)
        self._progress.pack(pady=(0, 32))

        # ESC hint
        ctk.CTkLabel(
            container,
            text='Press ESC to dismiss',
            text_color=TEXT_SEC,
            font=ctk.CTkFont(size=12),
        ).pack()

        self._window = win

        # Ensure the window grabs focus
        win.focus_force()
        win.lift()

    # ═══════════════════════════════════════════════════════════════════════
    # Countdown timer
    # ═══════════════════════════════════════════════════════════════════════

    _TICK_MS: int = 100  # Update every 100 ms for smooth progress

    def _start_countdown(self) -> None:
        """Begin the countdown loop."""
        self._tick()

    def _tick(self) -> None:
        """Handle a single countdown tick."""
        if self._window is None or not self._window.winfo_exists():
            return

        self._remaining_ms -= self._TICK_MS
        if self._remaining_ms <= 0:
            self._remaining_ms = 0
            self._update_display()
            self._complete()
            return

        self._update_display()
        self._timer_id = self._window.after(self._TICK_MS, self._tick)

    def _update_display(self) -> None:
        """Update countdown label and progress bar."""
        secs_left = max(0, math.ceil(self._remaining_ms / 1000))
        self._countdown_label.configure(text=str(secs_left))

        fraction = self._remaining_ms / self._total_ms if self._total_ms > 0 else 0
        self._progress.set(max(0.0, min(1.0, fraction)))

    def _complete(self) -> None:
        """Handle natural countdown completion."""
        self._stop_timers()
        if self._window is not None and self._window.winfo_exists():
            self._window.destroy()
            self._window = None
        if self._on_complete is not None:
            try:
                self._on_complete()
            except Exception:
                pass

    # ═══════════════════════════════════════════════════════════════════════
    # Pulse animation for the eye icon
    # ═══════════════════════════════════════════════════════════════════════

    _PULSE_INTERVAL_MS: int = 50

    def _start_pulse(self) -> None:
        """Start the subtle pulsing animation on the eye icon."""
        self._pulse_step()

    def _pulse_step(self) -> None:
        """Advance the pulse animation by one frame."""
        if self._window is None or not self._window.winfo_exists():
            return

        self._pulse_phase += 0.08
        # Scale factor oscillates between ~0.9 and 1.1
        scale = 1.0 + 0.08 * math.sin(self._pulse_phase)
        # Approximate scaling via font size (base 60)
        font_size = int(60 * scale)
        try:
            self._eye_label.configure(font=ctk.CTkFont(size=font_size))
        except Exception:
            pass

        self._pulse_id = self._window.after(self._PULSE_INTERVAL_MS, self._pulse_step)

    # ═══════════════════════════════════════════════════════════════════════
    # Timer cleanup
    # ═══════════════════════════════════════════════════════════════════════

    def _stop_timers(self) -> None:
        """Cancel all pending ``after`` callbacks."""
        if self._window is not None and self._window.winfo_exists():
            if self._timer_id is not None:
                try:
                    self._window.after_cancel(self._timer_id)
                except Exception:
                    pass
                self._timer_id = None

            if self._pulse_id is not None:
                try:
                    self._window.after_cancel(self._pulse_id)
                except Exception:
                    pass
                self._pulse_id = None
