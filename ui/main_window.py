"""
LagroEyewear Main Window Module.

Three-column dashboard displaying live webcam feed, blink-rate statistics,
a matplotlib chart, circular break timer, activity log, and settings panel.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from typing import Any, Deque, Dict, List, Optional

import customtkinter as ctk

try:
    import cv2
    import numpy as np
except ImportError:  # pragma: no cover
    cv2 = None  # type: ignore[assignment]
    np = None  # type: ignore[assignment]

try:
    from PIL import Image as PILImage
    from PIL import ImageTk
except ImportError:  # pragma: no cover
    PILImage = None  # type: ignore[assignment]

try:
    import matplotlib

    matplotlib.use('Agg')  # Non-interactive backend (we embed manually)
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
except ImportError:  # pragma: no cover
    plt = None  # type: ignore[assignment]
    FigureCanvasTkAgg = None  # type: ignore[assignment]

from core.blink_detector import BlinkDetector
from core.session_manager import SessionManager
from core.database import Database
from ui.components import (
    StatCard,
    CircularTimer,
    ActivityLog,
    SettingsPanel,
    InfoButton,
)
from ui.overlay import BreakOverlay
from ui.tray import SystemTray
from utils.settings import Settings
from utils.notifications import send_notification, notify_low_blink_rate, notify_break_time
from utils.autostart import enable_autostart, disable_autostart

logger = logging.getLogger(__name__)

# ── Color Palette ──────────────────────────────────────────────────────────────
BG = '#0D1117'
CARD_BG = '#161B22'
ACCENT = '#4A90FF'
GREEN = '#00E5A0'
AMBER = '#FFB800'
RED = '#FF4D4D'
TEXT = '#E6EDF3'
TEXT_SEC = '#8B949E'


class MainWindow(ctk.CTk):
    """Primary application window — a three-column blink-rate dashboard.

    Orchestrates the webcam feed, blink detection, session management,
    break scheduling, system tray, and all UI sub-components.
    """

    # ── Timing constants (milliseconds) ───────────────────────────────────
    _WEBCAM_INTERVAL_MS: int = 33      # ~30 fps
    _STATS_INTERVAL_MS: int = 1000     # 1 s
    _CHART_INTERVAL_MS: int = 5000     # 5 s
    _BREAK_TIMER_MS: int = 1000        # 1 s

    def __init__(self) -> None:
        super().__init__()

        # ── Window configuration ───────────────────────────────────────────
        self.title('LagroEyewear')
        self.geometry('1200x750')
        self.minsize(1000, 650)
        self.configure(fg_color=BG)
        ctk.set_appearance_mode('dark')

        # ── Core objects ───────────────────────────────────────────────────
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        settings_path = os.path.join(base_dir, 'settings.json')
        db_dir = os.path.join(base_dir, 'data')
        os.makedirs(db_dir, exist_ok=True)
        db_path = os.path.join(db_dir, 'lagroeyewear.db')

        self._settings = Settings(settings_path)
        self._db = Database(db_path)
        self._session = SessionManager(self._db, self._settings)
        self._detector = BlinkDetector()
        self._overlay = BreakOverlay(self)
        self._tray = SystemTray(self)

        # ── State ──────────────────────────────────────────────────────────
        self._paused: bool = False
        self._break_active: bool = False
        self._session_start: float = time.time()
        self._last_break_time: float = time.time()
        self._blink_history: Deque[tuple[float, float]] = deque(maxlen=120)
        self._current_blink_rate: float = 0.0
        self._last_low_blink_notif_time: float = 0.0

        # ── Build UI ──────────────────────────────────────────────────────
        self._setup_top_bar()
        self._setup_content_area()
        self._setup_status_bar()

        # ── System tray ────────────────────────────────────────────────────
        self._tray.setup()

        # ── Window-close protocol: minimise to tray ────────────────────────
        self.protocol('WM_DELETE_WINDOW', self.minimize_to_tray)

        # ── Start core ─────────────────────────────────────────────────────
        try:
            self._detector.start()
            self._session.start_session()
        except Exception as exc:
            logger.error('Failed to start core services: %s', exc)

        # ── Kick off periodic updates ──────────────────────────────────────
        self._update_webcam_feed()
        self._update_stats()
        self._update_chart()
        self._update_break_timer()

        # Log startup
        self._activity_log.add_event('LagroEyewear started', ACCENT)

        # ── Apply persisted settings ───────────────────────────────────────
        try:
            if self._settings.data:
                self._settings_panel.set_values(self._settings.data)
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════════════════════
    # Layout helpers
    # ═══════════════════════════════════════════════════════════════════════

    # ── Top Bar ────────────────────────────────────────────────────────────
    def _setup_top_bar(self) -> None:
        """Build the full-width top bar with branding and controls."""
        bar = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=0, height=52)
        bar.pack(fill='x', side='top')
        bar.pack_propagate(False)

        # Left: branding
        brand = ctk.CTkLabel(
            bar,
            text='👁️  LagroEyewear',
            text_color=TEXT,
            font=ctk.CTkFont(size=20, weight='bold'),
        )
        brand.pack(side='left', padx=18)

        # Centre: dashboard label
        centre_lbl = ctk.CTkLabel(
            bar,
            text='MAIN DASHBOARD',
            text_color=TEXT_SEC,
            font=ctk.CTkFont(size=12),
        )
        centre_lbl.pack(side='left', expand=True)

        # Right cluster
        right_frame = ctk.CTkFrame(bar, fg_color='transparent')
        right_frame.pack(side='right', padx=14)

        # Webcam status dot + label
        self._cam_dot = ctk.CTkLabel(
            right_frame, text='●', text_color=GREEN,
            font=ctk.CTkFont(size=10), width=14,
        )
        self._cam_dot.pack(side='left', padx=(0, 2))
        self._cam_status_lbl = ctk.CTkLabel(
            right_frame, text='Webcam Active', text_color=TEXT_SEC,
            font=ctk.CTkFont(size=11),
        )
        self._cam_status_lbl.pack(side='left', padx=(0, 12))

        # Info button
        self._info_btn = InfoButton(right_frame)
        self._info_btn.pack(side='left', padx=4)

        # Minimise-to-tray button
        tray_btn = ctk.CTkButton(
            right_frame, text='—', width=28, height=28, corner_radius=6,
            fg_color='#21262D', hover_color='#30363D', text_color=TEXT,
            font=ctk.CTkFont(size=16), command=self.minimize_to_tray,
        )
        tray_btn.pack(side='left', padx=4)

        # Settings gear button
        gear_btn = ctk.CTkButton(
            right_frame, text='⚙', width=28, height=28, corner_radius=6,
            fg_color='#21262D', hover_color='#30363D', text_color=TEXT,
            font=ctk.CTkFont(size=16), command=self._toggle_settings,
        )
        gear_btn.pack(side='left', padx=4)

    # ── Content area (three columns) ──────────────────────────────────────
    def _setup_content_area(self) -> None:
        """Create the 3-column grid: left (feed), centre (stats), right (controls)."""
        content = ctk.CTkFrame(self, fg_color='transparent')
        content.pack(fill='both', expand=True, padx=12, pady=8)

        content.columnconfigure(0, weight=1)    # left
        content.columnconfigure(1, weight=12)   # centre (1.2× via 12/10)
        content.columnconfigure(2, weight=10)   # right
        content.rowconfigure(0, weight=1)

        self._left_col = ctk.CTkFrame(content, fg_color='transparent')
        self._left_col.grid(row=0, column=0, sticky='nsew', padx=(0, 6))

        self._center_col = ctk.CTkFrame(content, fg_color='transparent')
        self._center_col.grid(row=0, column=1, sticky='nsew', padx=6)

        self._right_col = ctk.CTkFrame(content, fg_color='transparent')
        self._right_col.grid(row=0, column=2, sticky='nsew', padx=(6, 0))

        self._setup_left_column()
        self._setup_center_column()
        self._setup_right_column()

    # ── Left Column: Live Feed ─────────────────────────────────────────────
    def _setup_left_column(self) -> None:
        """Webcam feed display with rounded card and status label."""
        feed_card = ctk.CTkFrame(self._left_col, fg_color=CARD_BG, corner_radius=12)
        feed_card.pack(fill='both', expand=True)

        self._feed_label = ctk.CTkLabel(
            feed_card,
            text='Camera initialising…',
            text_color=TEXT_SEC,
            font=ctk.CTkFont(size=12),
        )
        self._feed_label.pack(fill='both', expand=True, padx=8, pady=8)

        self._feed_status = ctk.CTkLabel(
            self._left_col,
            text='● Tracking Active',
            text_color=GREEN,
            font=ctk.CTkFont(size=12, weight='bold'),
            anchor='w',
        )
        self._feed_status.pack(fill='x', padx=4, pady=(6, 0))

    # ── Centre Column: Stats + Chart ──────────────────────────────────────
    def _setup_center_column(self) -> None:
        """Three stat cards in a row and a matplotlib blink-rate chart."""
        # Stat cards row
        stats_row = ctk.CTkFrame(self._center_col, fg_color='transparent')
        stats_row.pack(fill='x', pady=(0, 8))

        self._blink_card = StatCard(
            stats_row, title='Blink Rate', value='-- bpm',
            status_text='Monitoring', status_color=GREEN,
        )
        self._blink_card.pack(side='left', fill='both', expand=True, padx=(0, 4))

        self._screen_card = StatCard(
            stats_row, title='Screen Time', value='00:00',
            status_text='Session active', status_color=ACCENT,
        )
        self._screen_card.pack(side='left', fill='both', expand=True, padx=4)

        self._strain_card = StatCard(
            stats_row, title='Eye Strain Score', value='0',
            status_text='Low', status_color=GREEN,
        )
        self._strain_card.pack(side='left', fill='both', expand=True, padx=(4, 0))

        # Chart frame
        chart_frame = ctk.CTkFrame(self._center_col, fg_color=CARD_BG, corner_radius=12)
        chart_frame.pack(fill='both', expand=True)

        self._chart_canvas: Optional[Any] = None
        self._fig = None
        self._ax = None

        if plt is not None and FigureCanvasTkAgg is not None:
            fig, ax = plt.subplots(figsize=(5, 2.5))
            fig.patch.set_facecolor(CARD_BG)
            ax.set_facecolor(CARD_BG)

            # Dark-themed axes
            for spine in ax.spines.values():
                spine.set_color('#21262D')
            ax.tick_params(colors=TEXT_SEC, labelsize=8)
            ax.xaxis.label.set_color(TEXT_SEC)
            ax.yaxis.label.set_color(TEXT_SEC)
            ax.set_title('Blink Rate Over Time', color=TEXT, fontsize=11, pad=10)
            ax.set_xlabel('Time (last 10 min)', fontsize=9)
            ax.set_ylabel('Blinks / min', fontsize=9)
            ax.grid(True, color='#21262D', linewidth=0.5, alpha=0.6)

            # Threshold line (red dashed at y=12)
            ax.axhline(y=12, color=RED, linestyle='--', linewidth=0.8, alpha=0.6)

            # Healthy zone shading (15-20 bpm)
            ax.axhspan(15, 20, color=GREEN, alpha=0.06)

            fig.tight_layout(pad=1.5)

            canvas = FigureCanvasTkAgg(fig, master=chart_frame)
            canvas.get_tk_widget().pack(fill='both', expand=True, padx=8, pady=8)
            canvas.draw()

            self._fig = fig
            self._ax = ax
            self._chart_canvas = canvas

    # ── Right Column: Timer, Controls, Settings, Log ──────────────────────
    def _setup_right_column(self) -> None:
        """Circular timer, action buttons, settings, and activity log."""
        # Circular timer
        timer_card = ctk.CTkFrame(self._right_col, fg_color=CARD_BG, corner_radius=12)
        timer_card.pack(fill='x', pady=(0, 8))

        self._timer = CircularTimer(timer_card, size=180)
        self._timer.pack(padx=10, pady=12)

        # Force Break button
        self._break_btn = ctk.CTkButton(
            self._right_col,
            text='Force Break Now',
            fg_color=ACCENT,
            hover_color='#6BABFF',
            text_color='#FFFFFF',
            font=ctk.CTkFont(size=13, weight='bold'),
            corner_radius=8,
            height=38,
            command=self.force_break,
        )
        self._break_btn.pack(fill='x', pady=(0, 6))

        # Pause toggle
        self._pause_btn = ctk.CTkButton(
            self._right_col,
            text='Pause Monitoring',
            fg_color='#21262D',
            hover_color='#30363D',
            text_color=TEXT,
            font=ctk.CTkFont(size=12),
            corner_radius=8,
            height=34,
            command=self.toggle_pause,
        )
        self._pause_btn.pack(fill='x', pady=(0, 8))

        # Settings panel (collapsible)
        self._settings_panel = SettingsPanel(
            self._right_col,
            on_change=self._on_settings_change,
        )
        self._settings_panel.pack(fill='x', pady=(0, 8))

        # Activity log
        self._activity_log = ActivityLog(self._right_col)
        self._activity_log.pack(fill='both', expand=True)

    # ── Status Bar ────────────────────────────────────────────────────────
    def _setup_status_bar(self) -> None:
        """Bottom status bar reflecting current eye-health level."""
        bar = ctk.CTkFrame(self, fg_color=GREEN, corner_radius=0, height=38)
        bar.pack(fill='x', side='bottom')
        bar.pack_propagate(False)

        self._status_bar = bar

        self._status_msg = ctk.CTkLabel(
            bar,
            text='👁️  Eyes are healthy — Keep going!',
            text_color='#FFFFFF',
            font=ctk.CTkFont(size=12, weight='bold'),
        )
        self._status_msg.pack(side='left', padx=16)

        # Right-side buttons
        right = ctk.CTkFrame(bar, fg_color='transparent')
        right.pack(side='right', padx=10)

        ctk.CTkButton(
            right, text='Force Break Now', height=26, corner_radius=6,
            fg_color='#2D5A3D', hover_color='#3D7A5D',
            text_color='#FFFFFF', font=ctk.CTkFont(size=11),
            command=self.force_break,
        ).pack(side='left', padx=4)

        ctk.CTkButton(
            right, text='Settings', height=26, corner_radius=6,
            fg_color='#2D5A3D', hover_color='#3D7A5D',
            text_color='#FFFFFF', font=ctk.CTkFont(size=11),
            command=self._toggle_settings,
        ).pack(side='left', padx=4)

    # ═══════════════════════════════════════════════════════════════════════
    # Periodic update loops
    # ═══════════════════════════════════════════════════════════════════════

    def _update_webcam_feed(self) -> None:
        """Grab a frame from :class:`BlinkDetector`, convert, and display (~30 fps)."""
        if not self._paused:
            try:
                frame = self._detector.get_frame()
                if frame is not None and cv2 is not None and PILImage is not None:
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pil_img = PILImage.fromarray(rgb)

                    # Resize to fit the feed label
                    display_w, display_h = 400, 300
                    pil_img = pil_img.resize(
                        (display_w, display_h), PILImage.LANCZOS
                    )

                    ctk_img = ctk.CTkImage(
                        light_image=pil_img,
                        dark_image=pil_img,
                        size=(display_w, display_h),
                    )
                    self._feed_label.configure(image=ctk_img, text='')
                    self._feed_label._ctk_image = ctk_img  # prevent GC

                    # Update feed status based on face detection
                    if self._detector.is_face_detected():
                        self._feed_status.configure(
                            text='● Tracking Active', text_color=GREEN
                        )
                        self._cam_dot.configure(text_color=GREEN)
                        self._cam_status_lbl.configure(text='Webcam Active')
                    else:
                        self._feed_status.configure(
                            text='● No Face Detected', text_color=AMBER
                        )
                        self._cam_dot.configure(text_color=AMBER)
                        self._cam_status_lbl.configure(text='No Face')
                else:
                    self._feed_status.configure(
                        text='● Camera Off', text_color=RED
                    )
                    self._cam_dot.configure(text_color=RED)
                    self._cam_status_lbl.configure(text='Camera Off')
            except Exception as exc:
                logger.debug('Webcam update error: %s', exc)

        self.after(self._WEBCAM_INTERVAL_MS, self._update_webcam_feed)

    def _update_stats(self) -> None:
        """Refresh stat cards and check break/alert thresholds (1 s interval)."""
        if not self._paused:
            try:
                # Blink rate
                blink_rate = self._detector.get_blink_rate()
                self._current_blink_rate = blink_rate

                if blink_rate >= 15:
                    status_text, status_color = 'Healthy', GREEN
                elif blink_rate >= 12:
                    status_text, status_color = 'Low', AMBER
                else:
                    status_text, status_color = 'Very Low', RED

                self._blink_card.update(
                    f'{blink_rate:.0f} bpm', status_text, status_color,
                )

                # Screen time
                elapsed = time.time() - self._session_start
                mins, secs = divmod(int(elapsed), 60)
                hrs, mins = divmod(mins, 60)
                if hrs > 0:
                    self._screen_card.update(
                        f'{hrs:02d}:{mins:02d}:{secs:02d}',
                        'Session active', ACCENT,
                    )
                else:
                    self._screen_card.update(
                        f'{mins:02d}:{secs:02d}',
                        'Session active', ACCENT,
                    )

                # Eye strain score (simple heuristic)
                strain = self._compute_strain_score(blink_rate, elapsed)
                if strain < 30:
                    s_text, s_color = 'Low', GREEN
                elif strain < 60:
                    s_text, s_color = 'Moderate', AMBER
                else:
                    s_text, s_color = 'High', RED
                self._strain_card.update(f'{strain:.0f}', s_text, s_color)

                # Store blink data point for chart
                self._blink_history.append((time.time(), blink_rate))

                # Update status bar
                self._update_status_bar(blink_rate)

                # Update tray icon colour
                if blink_rate >= 15:
                    self._tray.update_icon('good')
                elif blink_rate >= 12:
                    self._tray.update_icon('warning')
                else:
                    self._tray.update_icon('danger')

                # Check for low-blink notification
                settings_vals = self._settings_panel.get_values()
                threshold = settings_vals.get('low_blink_threshold', 12)
                if blink_rate > 0 and blink_rate < threshold:
                    if settings_vals.get('notifications', True):
                        now = time.time()
                        # Only notify at most once every 5 minutes (300 seconds)
                        if now - getattr(self, '_last_low_blink_notif_time', 0) > 300.0:
                            try:
                                notify_low_blink_rate(blink_rate)
                                self._last_low_blink_notif_time = now
                            except Exception:
                                pass

                # Check if break is needed
                self._check_break_needed()

            except Exception as exc:
                logger.debug('Stats update error: %s', exc)

        self.after(self._STATS_INTERVAL_MS, self._update_stats)

    def _update_chart(self) -> None:
        """Redraw the matplotlib blink-rate chart (5 s interval)."""
        if self._ax is not None and self._chart_canvas is not None:
            try:
                ax = self._ax
                # Clear previous line data (keep threshold line and shading)
                for line in ax.get_lines():
                    if line.get_linestyle() != '--':
                        line.remove()
                # Remove previous fill collections beyond the first (healthy zone)
                while len(ax.collections) > 1:
                    ax.collections[-1].remove()

                if self._blink_history:
                    now = time.time()
                    times: List[float] = []
                    rates: List[float] = []
                    for t, r in self._blink_history:
                        # Show last 10 minutes
                        if now - t <= 600:
                            times.append((t - now) / 60.0)  # minutes ago
                            rates.append(r)

                    if times:
                        ax.plot(times, rates, color=ACCENT, linewidth=1.5, alpha=0.9)
                        ax.fill_between(
                            times, rates, alpha=0.15, color=ACCENT
                        )

                self._chart_canvas.draw_idle()
            except Exception as exc:
                logger.debug('Chart update error: %s', exc)

        self.after(self._CHART_INTERVAL_MS, self._update_chart)

    def _update_break_timer(self) -> None:
        """Update the circular break-countdown timer (1 s interval)."""
        if not self._paused and not self._break_active:
            try:
                settings_vals = self._settings_panel.get_values()
                interval_s = settings_vals.get('break_interval', 20) * 60
                elapsed_since_break = time.time() - self._last_break_time
                remaining = max(0, int(interval_s - elapsed_since_break))
                self._timer.update(remaining, interval_s)
            except Exception as exc:
                logger.debug('Break timer update error: %s', exc)

        self.after(self._BREAK_TIMER_MS, self._update_break_timer)

    # ═══════════════════════════════════════════════════════════════════════
    # Break management
    # ═══════════════════════════════════════════════════════════════════════

    def _check_break_needed(self) -> None:
        """Trigger a break if the configured interval has elapsed."""
        if self._break_active or self._paused:
            return
        settings_vals = self._settings_panel.get_values()
        interval_s = settings_vals.get('break_interval', 20) * 60
        if time.time() - self._last_break_time >= interval_s:
            self.force_break()

    def force_break(self) -> None:
        """Trigger the fullscreen break overlay."""
        if self._break_active:
            return
        self._break_active = True
        self._activity_log.add_event('Break started', ACCENT)

        # Send notification
        try:
            settings_vals = self._settings_panel.get_values()
            if settings_vals.get('notifications', True):
                notify_break_time()
        except Exception:
            pass

        self._overlay.show(
            duration=20,
            on_complete=lambda: self._on_break_complete(dismissed_early=False),
            on_dismiss=lambda: self._on_break_complete(dismissed_early=True),
        )

    def _on_break_complete(self, dismissed_early: bool = False) -> None:
        """Handle break completion or early dismissal.

        Args:
            dismissed_early: ``True`` if the user pressed ESC.
        """
        self._break_active = False
        self._last_break_time = time.time()

        if dismissed_early:
            self._activity_log.add_event('Break dismissed early', AMBER)
        else:
            self._activity_log.add_event('Break completed ✓', GREEN)

        try:
            trigger = 'scheduled'
            self._session.record_break(trigger_type=trigger, duration=20, dismissed_early=dismissed_early)
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════════════════════
    # Controls
    # ═══════════════════════════════════════════════════════════════════════

    def toggle_pause(self) -> None:
        """Pause or resume blink monitoring."""
        self._paused = not self._paused
        if self._paused:
            self._pause_btn.configure(text='Resume Monitoring')
            self._activity_log.add_event('Monitoring paused', AMBER)
            self._feed_status.configure(text='● Paused', text_color=TEXT_SEC)
        else:
            self._pause_btn.configure(text='Pause Monitoring')
            self._activity_log.add_event('Monitoring resumed', GREEN)

    def minimize_to_tray(self) -> None:
        """Hide the main window and show the system-tray icon."""
        self.withdraw()
        self._tray.show()
        self._activity_log.add_event('Minimised to tray', TEXT_SEC)

    def show_window(self) -> None:
        """Restore the main window from the system tray."""
        self.deiconify()
        self.lift()
        self.focus_force()

    def quit_app(self) -> None:
        """Perform a clean shutdown of all subsystems and exit."""
        logger.info('Shutting down LagroEyewear…')
        try:
            self._detector.stop()
        except Exception:
            pass
        try:
            self._session.end_session()
        except Exception:
            pass
        try:
            self._db.close()
        except Exception:
            pass
        try:
            self._tray.stop()
        except Exception:
            pass
        self.destroy()

    # ═══════════════════════════════════════════════════════════════════════
    # Settings
    # ═══════════════════════════════════════════════════════════════════════

    def _on_settings_change(self, settings: Dict[str, Any]) -> None:
        """Apply new settings when the user adjusts a control.

        Args:
            settings: Dictionary of current setting values.
        """
        try:
            for key, value in settings.items():
                self._settings.set(key, value)
        except Exception:
            pass

        # Apply auto-start setting immediately
        try:
            if 'start_with_system' in settings:
                if settings['start_with_system']:
                    enable_autostart()
                    self._activity_log.add_event('Auto-start enabled', GREEN)
                else:
                    disable_autostart()
                    self._activity_log.add_event('Auto-start disabled', AMBER)
        except Exception:
            pass

        self._activity_log.add_event('Settings updated', ACCENT)

    def _toggle_settings(self) -> None:
        """Programmatically toggle the settings panel open/closed."""
        # Delegate to the panel's own toggle
        self._settings_panel._toggle()

    # ═══════════════════════════════════════════════════════════════════════
    # Helpers
    # ═══════════════════════════════════════════════════════════════════════

    def _update_status_bar(self, blink_rate: float) -> None:
        """Update the bottom status bar colour and message.

        Args:
            blink_rate: Current blinks per minute.
        """
        if blink_rate >= 15:
            self._status_bar.configure(fg_color=GREEN)
            self._status_msg.configure(
                text='👁️  Eyes are healthy — Keep going!'
            )
        elif blink_rate >= 12:
            self._status_bar.configure(fg_color=AMBER)
            self._status_msg.configure(
                text='⚠️  Blink rate is low — Consider a break'
            )
        else:
            self._status_bar.configure(fg_color=RED)
            self._status_msg.configure(
                text='🔴  Eye strain detected — Take a break now!'
            )

    @staticmethod
    def _compute_strain_score(blink_rate: float, session_seconds: float) -> float:
        """Compute a simple eye-strain heuristic (0–100).

        Lower blink rates and longer unbroken sessions increase the score.

        Args:
            blink_rate: Current blinks per minute.
            session_seconds: Seconds since session start.

        Returns:
            Strain score between 0 and 100.
        """
        # Blink contribution (lower blink → higher strain)
        if blink_rate >= 15:
            blink_score = 0.0
        elif blink_rate >= 12:
            blink_score = 30.0
        elif blink_rate >= 8:
            blink_score = 55.0
        else:
            blink_score = 80.0

        # Time contribution (longer sessions → higher strain)
        minutes = session_seconds / 60.0
        time_score = min(20.0, minutes * 0.5)

        return min(100.0, blink_score + time_score)
