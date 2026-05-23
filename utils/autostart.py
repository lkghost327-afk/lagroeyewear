"""
LagroEyewear Auto-Start Module
================================

Cross-platform auto-start management. Allows LagroEyewear to launch
automatically when the operating system boots.

Supported platforms:
    - **Windows**: Uses the ``HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run``
      registry key.
    - **macOS**: Creates a LaunchAgent plist in ``~/Library/LaunchAgents/``.
    - **Linux**: Creates a ``.desktop`` file in ``~/.config/autostart/``.
"""

import os
import sys
import platform
from typing import Optional


# ── Constants ──────────────────────────────────────────────────────────────────
APP_NAME: str = "LagroEyecare"
_REGISTRY_KEY: str = r"Software\Microsoft\Windows\CurrentVersion\Run"
_PLIST_NAME: str = "com.lagroeyecare.app.plist"
_DESKTOP_NAME: str = "lagroeyecare.desktop"


def _get_exe_path() -> str:
    """Return the path to the running executable or script.

    When packaged with PyInstaller, ``sys.executable`` points to the .exe.
    When running as a script, it returns the python interpreter path along
    with the main script.

    Returns:
        The command string to launch the application.
    """
    if getattr(sys, 'frozen', False):
        # Running as a PyInstaller bundle
        return sys.executable
    else:
        # Running as a script — use python + main.py
        main_py = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'main.py',
        )
        return f'"{sys.executable}" "{main_py}"'


# ══════════════════════════════════════════════════════════════════════════════
# Windows
# ══════════════════════════════════════════════════════════════════════════════

def _enable_windows() -> bool:
    """Add LagroEyecare to Windows startup via the registry.

    Returns:
        True if the registry key was set successfully.
    """
    try:
        import winreg
        exe_path = _get_exe_path()
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            _REGISTRY_KEY,
            0,
            winreg.KEY_SET_VALUE,
        )
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
        winreg.CloseKey(key)
        return True
    except Exception as exc:
        print(f"[AutoStart] Windows enable failed: {exc}")
        return False


def _disable_windows() -> bool:
    """Remove LagroEyecare from Windows startup registry.

    Returns:
        True if the key was removed or didn't exist.
    """
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            _REGISTRY_KEY,
            0,
            winreg.KEY_SET_VALUE,
        )
        try:
            winreg.DeleteValue(key, APP_NAME)
        except FileNotFoundError:
            pass  # Already removed
        winreg.CloseKey(key)
        return True
    except Exception as exc:
        print(f"[AutoStart] Windows disable failed: {exc}")
        return False


def _is_enabled_windows() -> bool:
    """Check if LagroEyecare is in the Windows startup registry.

    Returns:
        True if the registry entry exists.
    """
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            _REGISTRY_KEY,
            0,
            winreg.KEY_READ,
        )
        try:
            winreg.QueryValueEx(key, APP_NAME)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════════════
# macOS
# ══════════════════════════════════════════════════════════════════════════════

def _get_plist_path() -> str:
    """Return the path to the LaunchAgent plist file."""
    return os.path.expanduser(f"~/Library/LaunchAgents/{_PLIST_NAME}")


def _enable_macos() -> bool:
    """Create a LaunchAgent plist to auto-start on macOS.

    Returns:
        True if the plist was written successfully.
    """
    try:
        exe_path = _get_exe_path()
        plist_path = _get_plist_path()

        # Build the plist XML
        if getattr(sys, 'frozen', False):
            program_args = f"    <string>{exe_path}</string>"
        else:
            parts = exe_path.strip('"').split('" "')
            program_args = "\n".join(f"    <string>{p}</string>" for p in parts)

        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.lagroeyecare.app</string>
    <key>ProgramArguments</key>
    <array>
{program_args}
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
"""
        os.makedirs(os.path.dirname(plist_path), exist_ok=True)
        with open(plist_path, 'w', encoding='utf-8') as f:
            f.write(plist_content)
        return True
    except Exception as exc:
        print(f"[AutoStart] macOS enable failed: {exc}")
        return False


def _disable_macos() -> bool:
    """Remove the LaunchAgent plist on macOS.

    Returns:
        True if the plist was removed or didn't exist.
    """
    try:
        plist_path = _get_plist_path()
        if os.path.exists(plist_path):
            os.remove(plist_path)
        return True
    except Exception as exc:
        print(f"[AutoStart] macOS disable failed: {exc}")
        return False


def _is_enabled_macos() -> bool:
    """Check if the LaunchAgent plist exists on macOS."""
    return os.path.exists(_get_plist_path())


# ══════════════════════════════════════════════════════════════════════════════
# Linux
# ══════════════════════════════════════════════════════════════════════════════

def _get_desktop_path() -> str:
    """Return the path to the autostart .desktop file."""
    return os.path.expanduser(f"~/.config/autostart/{_DESKTOP_NAME}")


def _enable_linux() -> bool:
    """Create an autostart .desktop entry on Linux.

    Returns:
        True if the file was created successfully.
    """
    try:
        exe_path = _get_exe_path()
        desktop_path = _get_desktop_path()

        desktop_content = f"""[Desktop Entry]
Type=Application
Name=LagroEyecare
Comment=AI-Powered Eye Health Monitor
Exec={exe_path}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
"""
        os.makedirs(os.path.dirname(desktop_path), exist_ok=True)
        with open(desktop_path, 'w', encoding='utf-8') as f:
            f.write(desktop_content)
        return True
    except Exception as exc:
        print(f"[AutoStart] Linux enable failed: {exc}")
        return False


def _disable_linux() -> bool:
    """Remove the autostart .desktop entry on Linux."""
    try:
        desktop_path = _get_desktop_path()
        if os.path.exists(desktop_path):
            os.remove(desktop_path)
        return True
    except Exception as exc:
        print(f"[AutoStart] Linux disable failed: {exc}")
        return False


def _is_enabled_linux() -> bool:
    """Check if the autostart .desktop entry exists on Linux."""
    return os.path.exists(_get_desktop_path())


# ══════════════════════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════════════════════

def enable_autostart() -> bool:
    """Enable auto-start for the current platform.

    Returns:
        True if auto-start was enabled successfully.
    """
    system = platform.system()
    if system == 'Windows':
        return _enable_windows()
    elif system == 'Darwin':
        return _enable_macos()
    elif system == 'Linux':
        return _enable_linux()
    else:
        print(f"[AutoStart] Unsupported platform: {system}")
        return False


def disable_autostart() -> bool:
    """Disable auto-start for the current platform.

    Returns:
        True if auto-start was disabled successfully.
    """
    system = platform.system()
    if system == 'Windows':
        return _disable_windows()
    elif system == 'Darwin':
        return _disable_macos()
    elif system == 'Linux':
        return _disable_linux()
    else:
        print(f"[AutoStart] Unsupported platform: {system}")
        return False


def is_autostart_enabled() -> bool:
    """Check if auto-start is currently enabled.

    Returns:
        True if auto-start is active on the current platform.
    """
    system = platform.system()
    if system == 'Windows':
        return _is_enabled_windows()
    elif system == 'Darwin':
        return _is_enabled_macos()
    elif system == 'Linux':
        return _is_enabled_linux()
    else:
        return False
