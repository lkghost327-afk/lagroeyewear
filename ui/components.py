"""
LagroEyewear UI Components Module.

Reusable CustomTkinter widgets for the LagroEyewear dashboard including
stat cards, circular timer, activity log, settings panel, and info button.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

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


# ═══════════════════════════════════════════════════════════════════════════════
# StatCard
# ═══════════════════════════════════════════════════════════════════════════════

class StatCard(ctk.CTkFrame):
    """A rounded card displaying a single statistic with label, value, and
    coloured status indicator dot.

    Args:
        master: Parent widget.
        title: Small descriptive label shown above the value.
        value: Initial display value (default ``'--'``).
        status_text: Optional status text shown beside the dot.
        status_color: Colour of the status dot (default ``GREEN``).
    """

    def __init__(
        self,
        master: Any,
        title: str,
        value: str = '--',
        status_text: str = '',
        status_color: str = GREEN,
    ) -> None:
        super().__init__(
            master,
            fg_color=CARD_BG,
            corner_radius=12,
        )

        # Internal padding frame
        self._inner = ctk.CTkFrame(self, fg_color='transparent')
        self._inner.pack(fill='both', expand=True, padx=16, pady=14)

        # Title label (secondary text, small)
        self._title_label = ctk.CTkLabel(
            self._inner,
            text=title,
            text_color=TEXT_SEC,
            font=ctk.CTkFont(size=12),
            anchor='w',
        )
        self._title_label.pack(fill='x', anchor='w')

        # Value label (primary text, large & bold)
        self._value_label = ctk.CTkLabel(
            self._inner,
            text=value,
            text_color=TEXT,
            font=ctk.CTkFont(size=28, weight='bold'),
            anchor='w',
        )
        self._value_label.pack(fill='x', anchor='w', pady=(4, 6))

        # Status row (dot + text)
        self._status_frame = ctk.CTkFrame(self._inner, fg_color='transparent')
        self._status_frame.pack(fill='x', anchor='w')

        self._status_dot = ctk.CTkLabel(
            self._status_frame,
            text='●',
            text_color=status_color,
            font=ctk.CTkFont(size=10),
            width=14,
        )
        self._status_dot.pack(side='left')

        self._status_label = ctk.CTkLabel(
            self._status_frame,
            text=status_text,
            text_color=TEXT_SEC,
            font=ctk.CTkFont(size=11),
            anchor='w',
        )
        self._status_label.pack(side='left', padx=(4, 0))

    # ── Public API ─────────────────────────────────────────────────────────
    def update(
        self,
        value: str,
        status_text: str = '',
        status_color: Optional[str] = None,
    ) -> None:
        """Update the displayed value and optional status indicator.

        Args:
            value: New value string to display.
            status_text: New status text (empty string hides it).
            status_color: New dot colour; ``None`` keeps current colour.
        """
        self._value_label.configure(text=value)
        if status_text:
            self._status_label.configure(text=status_text)
        if status_color is not None:
            self._status_dot.configure(text_color=status_color)


# ═══════════════════════════════════════════════════════════════════════════════
# CircularTimer
# ═══════════════════════════════════════════════════════════════════════════════

class CircularTimer(ctk.CTkCanvas):
    """Canvas-based circular countdown timer showing time until the next break.

    Draws a depleting arc and centred MM:SS text.  Designed to sit inside a
    ``CARD_BG`` container.

    Args:
        master: Parent widget.
        size: Diameter in pixels (default ``200``).
    """

    _ARC_WIDTH: int = 8
    _PAD: int = 16  # inset from canvas edge

    def __init__(self, master: Any, size: int = 200) -> None:
        super().__init__(
            master,
            width=size,
            height=size,
            bg=CARD_BG,
            highlightthickness=0,
            bd=0,
        )
        self._size = size
        self._center = size // 2

        # Bounding box for the arc (inset by padding + half stroke)
        inset = self._PAD + self._ARC_WIDTH // 2
        self._bbox: Tuple[int, int, int, int] = (
            inset,
            inset,
            size - inset,
            size - inset,
        )

        # Draw initial static elements
        self._draw_static()

    # ── Internal drawing helpers ───────────────────────────────────────────
    def _draw_static(self) -> None:
        """Draw the background track ring and placeholder text."""
        self.delete('all')

        # Background track (subtle ring)
        self.create_oval(
            *self._bbox,
            outline='#21262D',
            width=self._ARC_WIDTH,
            tags='track',
        )

        # "Next break in" label
        self.create_text(
            self._center,
            self._center - 24,
            text='Next break in',
            fill=TEXT_SEC,
            font=('Segoe UI', 10),
            tags='label',
        )

        # Time text (placeholder)
        self.create_text(
            self._center,
            self._center + 8,
            text='--:--',
            fill=TEXT,
            font=('Segoe UI', 26, 'bold'),
            tags='time',
        )

    def update(self, remaining_seconds: int, total_seconds: int) -> None:
        """Redraw the arc and countdown text.

        Args:
            remaining_seconds: Seconds left until the break.
            total_seconds: Total duration of the break interval.
        """
        self.delete('arc')
        self.delete('time')
        self.delete('label')

        # Fraction remaining  (1.0 → full, 0.0 → empty)
        if total_seconds <= 0:
            fraction = 0.0
        else:
            fraction = max(0.0, min(1.0, remaining_seconds / total_seconds))

        extent = fraction * 360  # arc extent in degrees

        # Choose colour along ACCENT → GREEN gradient based on fraction
        arc_color = self._lerp_color(ACCENT, GREEN, 1.0 - fraction)

        # Draw progress arc (starts at 12-o'clock, sweeps counter-clockwise)
        if extent > 0:
            self.create_arc(
                *self._bbox,
                start=90,
                extent=extent,
                style='arc',
                outline=arc_color,
                width=self._ARC_WIDTH,
                tags='arc',
            )

        # "Next break in" label
        self.create_text(
            self._center,
            self._center - 24,
            text='Next break in',
            fill=TEXT_SEC,
            font=('Segoe UI', 10),
            tags='label',
        )

        # MM:SS text
        mins, secs = divmod(max(0, remaining_seconds), 60)
        time_str = f'{mins:02d}:{secs:02d}'
        self.create_text(
            self._center,
            self._center + 8,
            text=time_str,
            fill=TEXT,
            font=('Segoe UI', 26, 'bold'),
            tags='time',
        )

    # ── Colour interpolation ──────────────────────────────────────────────
    @staticmethod
    def _lerp_color(c1: str, c2: str, t: float) -> str:
        """Linearly interpolate between two hex colours.

        Args:
            c1: Start colour (hex string, e.g. ``'#4A90FF'``).
            c2: End colour.
            t: Interpolation factor ``[0, 1]``.

        Returns:
            Interpolated hex colour string.
        """
        r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
        r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        return f'#{r:02x}{g:02x}{b:02x}'


# ═══════════════════════════════════════════════════════════════════════════════
# ActivityLog
# ═══════════════════════════════════════════════════════════════════════════════

class ActivityLog(ctk.CTkFrame):
    """Scrollable log of recent application events.

    Displays up to 10 entries, each with a coloured dot, timestamp, and
    description.  Newest events appear at the top.

    Args:
        master: Parent widget.
    """

    _MAX_ENTRIES: int = 10

    def __init__(self, master: Any) -> None:
        super().__init__(master, fg_color=CARD_BG, corner_radius=12)

        # Title
        self._title = ctk.CTkLabel(
            self,
            text='Recent Activity',
            text_color=TEXT,
            font=ctk.CTkFont(size=14, weight='bold'),
            anchor='w',
        )
        self._title.pack(fill='x', padx=14, pady=(12, 6))

        # Scrollable container for log entries
        self._scroll = ctk.CTkScrollableFrame(
            self,
            fg_color='transparent',
            scrollbar_button_color='#21262D',
            scrollbar_button_hover_color='#30363D',
        )
        self._scroll.pack(fill='both', expand=True, padx=8, pady=(0, 8))

        # Internal list tracking entry widgets (newest first)
        self._entries: List[ctk.CTkFrame] = []

    # ── Public API ─────────────────────────────────────────────────────────
    def add_event(self, text: str, color: str = ACCENT) -> None:
        """Add an event to the top of the log.

        If the log exceeds ``_MAX_ENTRIES``, the oldest entry is removed.

        Args:
            text: Event description.
            color: Dot colour for the entry.
        """
        timestamp = datetime.now().strftime('%H:%M:%S')

        # Build row frame
        row = ctk.CTkFrame(self._scroll, fg_color='transparent')

        dot = ctk.CTkLabel(
            row,
            text='●',
            text_color=color,
            font=ctk.CTkFont(size=10),
            width=14,
        )
        dot.pack(side='left', padx=(4, 4))

        time_lbl = ctk.CTkLabel(
            row,
            text=timestamp,
            text_color=TEXT_SEC,
            font=ctk.CTkFont(size=11),
            width=60,
            anchor='w',
        )
        time_lbl.pack(side='left', padx=(0, 6))

        desc_lbl = ctk.CTkLabel(
            row,
            text=text,
            text_color=TEXT,
            font=ctk.CTkFont(size=11),
            anchor='w',
        )
        desc_lbl.pack(side='left', fill='x', expand=True)

        # Insert at the top
        row.pack(fill='x', pady=2, before=self._entries[0] if self._entries else None)
        self._entries.insert(0, row)

        # Evict oldest if over limit
        if len(self._entries) > self._MAX_ENTRIES:
            old = self._entries.pop()
            old.destroy()


# ═══════════════════════════════════════════════════════════════════════════════
# SettingsPanel
# ═══════════════════════════════════════════════════════════════════════════════

class SettingsPanel(ctk.CTkFrame):
    """Collapsible settings panel containing sliders and toggles for
    application preferences.

    Args:
        master: Parent widget.
        on_change: Optional callback invoked with the current settings dict
            whenever a value changes.
    """

    def __init__(
        self,
        master: Any,
        on_change: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        super().__init__(master, fg_color=CARD_BG, corner_radius=12)

        self._on_change = on_change
        self._expanded = False

        # ── Toggle button ──────────────────────────────────────────────────
        self._toggle_btn = ctk.CTkButton(
            self,
            text='⚙  Settings  ▸',
            fg_color='transparent',
            hover_color='#21262D',
            text_color=TEXT,
            font=ctk.CTkFont(size=13, weight='bold'),
            anchor='w',
            command=self._toggle,
            height=36,
        )
        self._toggle_btn.pack(fill='x', padx=10, pady=(8, 4))

        # ── Collapsible content frame ──────────────────────────────────────
        self._content = ctk.CTkFrame(self, fg_color='transparent')
        # Initially collapsed — *not* packed

        # ── Break interval slider (10–60 min) ─────────────────────────────
        self._break_label = self._make_label(self._content, 'Break Interval: 20 min')
        self._break_slider = ctk.CTkSlider(
            self._content,
            from_=10,
            to=60,
            number_of_steps=50,
            button_color=ACCENT,
            button_hover_color='#6BABFF',
            progress_color=ACCENT,
            fg_color='#21262D',
            command=self._on_break_slider,
        )
        self._break_slider.set(20)
        self._break_slider.pack(fill='x', padx=14, pady=(0, 10))

        # ── Low blink threshold slider (5–20 bpm) ─────────────────────────
        self._blink_label = self._make_label(self._content, 'Low Blink Threshold: 12 bpm')
        self._blink_slider = ctk.CTkSlider(
            self._content,
            from_=5,
            to=20,
            number_of_steps=15,
            button_color=ACCENT,
            button_hover_color='#6BABFF',
            progress_color=ACCENT,
            fg_color='#21262D',
            command=self._on_blink_slider,
        )
        self._blink_slider.set(12)
        self._blink_slider.pack(fill='x', padx=14, pady=(0, 10))

        # ── Notification toggle ────────────────────────────────────────────
        self._notif_var = ctk.BooleanVar(value=True)
        self._notif_row = self._make_switch_row(
            self._content,
            'Notifications',
            self._notif_var,
        )

        # ── Start minimized toggle ─────────────────────────────────────────
        self._minimized_var = ctk.BooleanVar(value=False)
        self._minimized_row = self._make_switch_row(
            self._content,
            'Start Minimized',
            self._minimized_var,
        )

        # ── Start with system toggle ───────────────────────────────────────
        self._autostart_var = ctk.BooleanVar(value=False)
        self._autostart_row = self._make_switch_row(
            self._content,
            'Start with System',
            self._autostart_var,
        )

    # ── Widget factory helpers ─────────────────────────────────────────────
    def _make_label(self, parent: Any, text: str) -> ctk.CTkLabel:
        """Create and pack a settings label."""
        lbl = ctk.CTkLabel(
            parent,
            text=text,
            text_color=TEXT_SEC,
            font=ctk.CTkFont(size=12),
            anchor='w',
        )
        lbl.pack(fill='x', padx=14, pady=(8, 2))
        return lbl

    def _make_switch_row(
        self,
        parent: Any,
        label_text: str,
        variable: ctk.BooleanVar,
    ) -> ctk.CTkFrame:
        """Create a label + switch row."""
        row = ctk.CTkFrame(parent, fg_color='transparent')
        row.pack(fill='x', padx=14, pady=6)

        lbl = ctk.CTkLabel(
            row,
            text=label_text,
            text_color=TEXT_SEC,
            font=ctk.CTkFont(size=12),
            anchor='w',
        )
        lbl.pack(side='left')

        switch = ctk.CTkSwitch(
            row,
            text='',
            variable=variable,
            onvalue=True,
            offvalue=False,
            button_color=ACCENT,
            button_hover_color='#6BABFF',
            progress_color=ACCENT,
            fg_color='#21262D',
            command=self._fire_change,
        )
        switch.pack(side='right')
        return row

    # ── Expand / Collapse ──────────────────────────────────────────────────
    def _toggle(self) -> None:
        """Toggle the settings panel open or closed."""
        self._expanded = not self._expanded
        if self._expanded:
            self._content.pack(fill='x', padx=4, pady=(0, 8))
            self._toggle_btn.configure(text='⚙  Settings  ▾')
        else:
            self._content.pack_forget()
            self._toggle_btn.configure(text='⚙  Settings  ▸')

    # ── Slider callbacks ──────────────────────────────────────────────────
    def _on_break_slider(self, value: float) -> None:
        """Handle break-interval slider movement."""
        val = int(round(value))
        self._break_label.configure(text=f'Break Interval: {val} min')
        self._fire_change()

    def _on_blink_slider(self, value: float) -> None:
        """Handle blink-threshold slider movement."""
        val = int(round(value))
        self._blink_label.configure(text=f'Low Blink Threshold: {val} bpm')
        self._fire_change()

    def _fire_change(self, *_args: Any) -> None:
        """Notify the ``on_change`` callback with current settings."""
        if self._on_change is not None:
            self._on_change(self.get_values())

    # ── Public API ─────────────────────────────────────────────────────────
    def get_values(self) -> Dict[str, Any]:
        """Return a dict of all current setting values.

        Returns:
            Dictionary with keys ``'break_interval'``, ``'low_blink_threshold'``,
            ``'notifications'``, and ``'start_minimized'``.
        """
        return {
            'break_interval': int(round(self._break_slider.get())),
            'low_blink_threshold': int(round(self._blink_slider.get())),
            'notifications': self._notif_var.get(),
            'start_minimized': self._minimized_var.get(),
            'start_with_system': self._autostart_var.get(),
        }

    def set_values(self, settings: Dict[str, Any]) -> None:
        """Populate controls from a settings dictionary.

        Args:
            settings: Dict whose keys match those returned by :meth:`get_values`.
        """
        if 'break_interval' in settings:
            val = int(settings['break_interval'])
            self._break_slider.set(val)
            self._break_label.configure(text=f'Break Interval: {val} min')

        if 'low_blink_threshold' in settings:
            val = int(settings['low_blink_threshold'])
            self._blink_slider.set(val)
            self._blink_label.configure(text=f'Low Blink Threshold: {val} bpm')

        if 'notifications' in settings:
            self._notif_var.set(bool(settings['notifications']))

        if 'start_minimized' in settings:
            self._minimized_var.set(bool(settings['start_minimized']))

        if 'start_with_system' in settings:
            self._autostart_var.set(bool(settings['start_with_system']))


# ═══════════════════════════════════════════════════════════════════════════════
# InfoButton
# ═══════════════════════════════════════════════════════════════════════════════

class InfoButton(ctk.CTkButton):
    """Small circular **?** button that opens a tooltip window explaining
    how EAR-based blink detection works.

    Args:
        master: Parent widget.
    """

    _EXPLANATION = (
        'How Blink Detection Works\n\n'
        'LagroEyewear uses MediaPipe Face Mesh to detect 468 facial landmarks '
        'in real time. For each eye, 6 key landmarks are tracked to calculate '
        'the Eye Aspect Ratio (EAR).\n\n'
        'EAR = (|p2-p6| + |p3-p5|) / (2 × |p1-p4|)\n\n'
        'When you blink, the EAR drops sharply below 0.25. By tracking this '
        'across consecutive frames, we accurately detect each blink.\n\n'
        'A healthy blink rate is 15-20 blinks per minute. When your rate '
        'drops below 12 blinks/min, it may indicate digital eye strain.'
    )

    def __init__(self, master: Any) -> None:
        super().__init__(
            master,
            text='?',
            width=28,
            height=28,
            corner_radius=14,
            fg_color='#21262D',
            hover_color='#30363D',
            text_color=TEXT,
            font=ctk.CTkFont(size=13, weight='bold'),
            command=self._show_popup,
        )
        self._popup: Optional[ctk.CTkToplevel] = None

    def _show_popup(self) -> None:
        """Open a small top-level window with EAR explanation text."""
        # Avoid multiple popups
        if self._popup is not None and self._popup.winfo_exists():
            self._popup.focus()
            return

        self._popup = ctk.CTkToplevel(self)
        self._popup.title('Blink Detection Info')
        self._popup.geometry('440x380')
        self._popup.resizable(False, False)
        self._popup.configure(fg_color=CARD_BG)

        # Keep on top of the main window
        self._popup.attributes('-topmost', True)
        self._popup.after(100, lambda: self._popup.attributes('-topmost', False))

        # Content
        text_label = ctk.CTkLabel(
            self._popup,
            text=self._EXPLANATION,
            text_color=TEXT,
            font=ctk.CTkFont(size=13),
            wraplength=400,
            justify='left',
            anchor='nw',
        )
        text_label.pack(fill='both', expand=True, padx=20, pady=20)

        # Close button
        close_btn = ctk.CTkButton(
            self._popup,
            text='Close',
            fg_color=ACCENT,
            hover_color='#6BABFF',
            text_color='#FFFFFF',
            font=ctk.CTkFont(size=13),
            corner_radius=8,
            command=self._popup.destroy,
            height=32,
        )
        close_btn.pack(pady=(0, 16))
