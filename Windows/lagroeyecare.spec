# -*- mode: python ; coding: utf-8 -*-
"""
LagroEyecare PyInstaller Spec File
====================================

Builds a single-file Windows executable named 'LagroEyecare.exe'.
Bundles the FaceLandmarker model, the app icon, and all dependencies.

Usage:
    pyinstaller lagroeyecare.spec
"""

import os
import sys

block_cipher = None

# ── Locate MediaPipe data files ────────────────────────────────────────────
# The new Tasks API needs the model bundles and any native libs
mediapipe_datas = []
try:
    import importlib
    mediapipe_path = os.path.dirname(importlib.import_module('mediapipe').__file__)

    # Include the entire mediapipe package data to ensure all native
    # libraries and task runners are bundled correctly
    for dirpath, dirnames, filenames in os.walk(mediapipe_path):
        for f in filenames:
            if f.endswith(('.pyd', '.so', '.dll', '.tflite', '.binarypb', '.txt', '.task')):
                src = os.path.join(dirpath, f)
                dst = os.path.relpath(dirpath, os.path.dirname(mediapipe_path))
                mediapipe_datas.append((src, dst))
except Exception as e:
    print(f"Warning: Could not locate mediapipe data files: {e}")

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets/icon.png', 'assets'),
        ('assets/face_landmarker.task', 'assets'),
        *mediapipe_datas,
    ],
    hiddenimports=[
        'mediapipe',
        'mediapipe.tasks',
        'mediapipe.tasks.python',
        'mediapipe.tasks.python.vision',
        'mediapipe.tasks.python.vision.face_landmarker',
        'mediapipe.tasks.python.core',
        'mediapipe.tasks.python.core.task_runner',
        'mediapipe.tasks.python.components',
        'mediapipe.tasks.python.components.containers',
        'customtkinter',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'PIL.ImageTk',
        'pystray',
        'pystray._win32',
        'plyer',
        'plyer.platforms.win.notification',
        'matplotlib',
        'matplotlib.backends.backend_tkagg',
        'numpy',
        'cv2',
        'sqlite3',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='LagroEyecare',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.png',
)
