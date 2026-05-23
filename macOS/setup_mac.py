"""
LagroEyecare — py2app Setup Script (macOS Native)
====================================================

Builds a native macOS .app bundle using py2app.

Usage:
    python3 setup_mac.py py2app
"""

from setuptools import setup

APP = ['main.py']
DATA_FILES = [
    ('assets', ['assets/icon.png', 'assets/face_landmarker.task']),
]
OPTIONS = {
    'argv_emulation': False,
    'iconfile': 'assets/icon.png',
    'plist': {
        'CFBundleName': 'LagroEyecare',
        'CFBundleDisplayName': 'LagroEyecare',
        'CFBundleIdentifier': 'com.lagroeyecare.app',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSCameraUsageDescription': 'LagroEyecare needs camera access to monitor your blink rate for eye health.',
        'NSHumanReadableCopyright': 'Copyright © 2026 LagroEyecare',
        'LSMinimumSystemVersion': '10.15',
    },
    'packages': [
        'mediapipe',
        'cv2',
        'customtkinter',
        'matplotlib',
        'numpy',
        'PIL',
        'pystray',
        'plyer',
    ],
    'includes': [
        'tkinter',
        'sqlite3',
        'mediapipe.tasks',
        'mediapipe.tasks.python',
        'mediapipe.tasks.python.vision',
        'mediapipe.tasks.python.vision.face_landmarker',
    ],
}

setup(
    app=APP,
    name='LagroEyecare',
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
