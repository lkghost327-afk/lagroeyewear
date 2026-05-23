"""
LagroEyewear System Tray Module.

Provides system-tray integration via ``pystray`` so the application can be
minimised to the notification area with a dynamically-coloured eye icon.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Optional

try:
    from PIL import Image, ImageDraw
except ImportError:  # pragma: no cover
    Image = None  # type: ignore[assignment,misc]
    ImageDraw = None  # type: ignore[assignment,misc]

try:
    import pystray
    from pystray import MenuItem, Menu
except ImportError:  # pragma: no cover
    pystray = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# ── Color Palette ──────────────────────────────────────────────────────────────
BG = '#0D1117'
ACCENT = '#4A90FF'
GREEN = '#00E5A0'
AMBER = '#FFB800'
RED = '#FF4D4D'
TEXT = '#E6EDF3'

# Status → colour mapping
_STATUS_COLORS: dict[str, str] = {
    'good': GREEN,
    'warning': AMBER,
    'danger': RED,
}


class SystemTray:
    """Manages the LagroEyewear system-tray icon and its context menu.

    The icon is a programmatically-drawn stylised eye whose colour reflects
    the user's current eye-health status.

    Args:
        app_ref: Reference to the main application object.  Must expose the
            methods ``show_window()``, ``force_break()``, ``toggle_pause()``,
            and ``quit_app()``.
    """

    def __init__(self, app_ref: Any) -> None:
        self._app = app_ref
        self._icon: Optional[Any] = None  # pystray.Icon
        self._thread: Optional[threading.Thread] = None
        self._current_color: str = GREEN

    # ═══════════════════════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════════════════════

    def setup(self) -> None:
        """Create the tray icon and start it in a background daemon thread."""
        if pystray is None or Image is None:
            logger.warning(
                'pystray or Pillow not installed — system tray disabled.'
            )
            return

        image = self._create_icon_image(self._current_color)
        menu = self._build_menu()

        self._icon = pystray.Icon(
            name='LagroEyewear',
            icon=image,
            title='LagroEyewear',
            menu=menu,
        )

        self._thread = threading.Thread(
            target=self._icon.run,
            daemon=True,
            name='SystemTrayThread',
        )
        self._thread.start()
        logger.info('System tray icon started.')

    def show(self) -> None:
        """Make the tray icon visible (re-run if stopped)."""
        if self._icon is None:
            self.setup()
        elif not self._icon.visible:
            self._icon.visible = True

    def hide(self) -> None:
        """Hide the tray icon without stopping the thread."""
        if self._icon is not None:
            try:
                self._icon.visible = False
            except Exception:
                pass

    def stop(self) -> None:
        """Stop the tray icon and its background thread."""
        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception:
                pass
            self._icon = None
        self._thread = None
        logger.info('System tray icon stopped.')

    def update_icon(self, status: str) -> None:
        """Regenerate the icon image with a colour matching *status*.

        Args:
            status: One of ``'good'``, ``'warning'``, or ``'danger'``.
        """
        color = _STATUS_COLORS.get(status, GREEN)
        self._current_color = color
        if self._icon is not None and Image is not None:
            try:
                self._icon.icon = self._create_icon_image(color)
            except Exception as exc:
                logger.debug('Failed to update tray icon: %s', exc)

    # ═══════════════════════════════════════════════════════════════════════
    # Menu
    # ═══════════════════════════════════════════════════════════════════════

    def _build_menu(self) -> Any:
        """Build the context menu for the tray icon.

        Returns:
            A ``pystray.Menu`` instance.
        """
        return Menu(
            MenuItem('Open LagroEyewear', self._on_open),
            Menu.SEPARATOR,
            MenuItem('Force Break', self._on_force_break),
            MenuItem('Pause/Resume Monitoring', self._on_toggle_pause),
            Menu.SEPARATOR,
            MenuItem('Quit', self._on_quit),
        )

    # ── Menu callbacks (dispatch to app_ref on the main thread) ────────────
    def _on_open(self, _icon: Any = None, _item: Any = None) -> None:
        """Handle 'Open LagroEyewear' menu click."""
        try:
            self._app.show_window()
        except Exception as exc:
            logger.error('Tray → show_window failed: %s', exc)

    def _on_force_break(self, _icon: Any = None, _item: Any = None) -> None:
        """Handle 'Force Break' menu click."""
        try:
            self._app.force_break()
        except Exception as exc:
            logger.error('Tray → force_break failed: %s', exc)

    def _on_toggle_pause(self, _icon: Any = None, _item: Any = None) -> None:
        """Handle 'Pause/Resume Monitoring' menu click."""
        try:
            self._app.toggle_pause()
        except Exception as exc:
            logger.error('Tray → toggle_pause failed: %s', exc)

    def _on_quit(self, _icon: Any = None, _item: Any = None) -> None:
        """Handle 'Quit' menu click."""
        try:
            self._app.quit_app()
        except Exception as exc:
            logger.error('Tray → quit_app failed: %s', exc)

    # ═══════════════════════════════════════════════════════════════════════
    # Icon Image Generation
    # ═══════════════════════════════════════════════════════════════════════

    @staticmethod
    def _create_icon_image(color: str) -> 'Image.Image':
        """Draw a 64×64 stylised eye icon in the given *color*.

        The icon consists of two mirrored arcs forming an almond-shaped eye
        outline with a filled circular iris/pupil in the centre.

        Args:
            color: Hex colour string for the eye outline and iris.

        Returns:
            A 64×64 RGBA :class:`PIL.Image.Image`.
        """
        size = 64
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Parse hex colour to RGB tuple
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        rgb = (r, g, b, 255)

        cx, cy = size // 2, size // 2

        # ── Eye outline (two arcs) ─────────────────────────────────────────
        # Upper arc
        draw.arc(
            [4, 8, 60, 52],
            start=200,
            end=340,
            fill=rgb,
            width=3,
        )
        # Lower arc
        draw.arc(
            [4, 12, 60, 56],
            start=20,
            end=160,
            fill=rgb,
            width=3,
        )

        # ── Iris (outer circle) ────────────────────────────────────────────
        iris_r = 10
        draw.ellipse(
            [cx - iris_r, cy - iris_r, cx + iris_r, cy + iris_r],
            fill=rgb,
        )

        # ── Pupil (inner dark circle) ─────────────────────────────────────
        pupil_r = 4
        draw.ellipse(
            [cx - pupil_r, cy - pupil_r, cx + pupil_r, cy + pupil_r],
            fill=(13, 17, 23, 255),  # BG colour
        )

        # ── Highlight (small white dot) ───────────────────────────────────
        hl_x, hl_y = cx - 3, cy - 3
        hl_r = 2
        draw.ellipse(
            [hl_x - hl_r, hl_y - hl_r, hl_x + hl_r, hl_y + hl_r],
            fill=(255, 255, 255, 200),
        )

        return img
