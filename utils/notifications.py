"""
LagroEyewear Notifications Module
==================================

Desktop notification helpers using the plyer library.
All notification calls are wrapped in try/except for cross-platform
safety — if plyer or the underlying OS notification system is
unavailable, errors are logged rather than crashing the app.
"""

from typing import Optional


def send_notification(
    title: str,
    message: str,
    timeout: int = 10,
) -> None:
    """Send a desktop notification to the user.

    Args:
        title: Notification title text.
        message: Notification body text.
        timeout: Seconds to display the notification (default 10).
    """
    try:
        from plyer import notification

        notification.notify(
            title=title,
            message=message,
            app_name="LagroEyewear",
            timeout=timeout,
        )
    except ImportError:
        print(f"[Notifications] plyer not installed — {title}: {message}")
    except Exception as exc:
        # Catch any platform-specific errors (e.g., missing dbus on Linux)
        print(f"[Notifications] Could not send notification — {exc}")


def notify_low_blink_rate(blink_rate: float) -> None:
    """Warn the user that their blink rate is dangerously low.

    Args:
        blink_rate: The current blinks-per-minute reading.
    """
    send_notification(
        title="⚠️ Low Blink Rate Detected",
        message=(
            f"Your blink rate has dropped to {blink_rate:.0f} blinks/min. "
            "Try to blink more frequently to reduce eye strain."
        ),
        timeout=8,
    )


def notify_break_time() -> None:
    """Remind the user to take a break."""
    send_notification(
        title="🧘 Time for a Break!",
        message=(
            "You've been working for a while. Look away from your screen, "
            "focus on something 20 feet away for 20 seconds."
        ),
        timeout=15,
    )


def notify_no_face() -> None:
    """Warn the user that no face is detected by the camera."""
    send_notification(
        title="👤 Face Not Detected",
        message=(
            "LagroEyewear cannot detect your face. "
            "Please ensure your webcam is unobstructed and you are in frame."
        ),
        timeout=10,
    )
