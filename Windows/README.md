# 🖥️ LagroEyecare — Windows Distribution

## Prerequisites

- **Python 3.10+** installed and on PATH
- **pip** package manager
- A webcam

## Quick Start (Run from Source)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Download the FaceLandmarker model (required, ~4 MB)
# Place it in assets/face_landmarker.task
# Download from: https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task

# 3. Run the app
python main.py
```

## Build Executable (.exe)

To create a standalone `LagroEyecare.exe` that runs without Python installed:

### Option 1: Use the Build Script

```bash
# Double-click build.bat or run from Command Prompt:
build.bat
```

The build script will:
1. Install Python dependencies
2. Install PyInstaller
3. Download the FaceLandmarker model (if not present)
4. Build the executable

### Option 2: Manual Build

```bash
# 1. Install PyInstaller
pip install pyinstaller

# 2. Download the model (if not present)
powershell -Command "Invoke-WebRequest -Uri 'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task' -OutFile 'assets\face_landmarker.task'"

# 3. Build the executable
pyinstaller lagroeyecare.spec

# 4. Find the executable
# The .exe will be in: dist/LagroEyecare.exe
```

## Auto-Start on Boot

LagroEyecare can automatically start when Windows boots up:

1. Open the app
2. Click **Settings** (⚙ gear icon)
3. Toggle **"Start with System"** ON

This adds a Windows Registry entry at:
```
HKCU\Software\Microsoft\Windows\CurrentVersion\Run\LagroEyecare
```

To disable, simply toggle it OFF in Settings.

## System Tray

- The app minimizes to the system tray (notification area)
- Right-click the tray icon for quick actions
- Close button minimizes to tray; use **Quit** from tray menu to fully exit

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "No webcam found" | Check webcam permissions in Windows Settings → Privacy → Camera |
| App doesn't start | Run from Command Prompt to see error messages |
| MediaPipe errors | Try `pip install mediapipe --upgrade` |
| Black webcam feed | Close other apps using the camera |
| Model not found | Download `face_landmarker.task` and place in `assets/` |

## File Locations

| File | Location |
|------|----------|
| Settings | `settings.json` (same directory as app) |
| Database | `data/lagroeyewear.db` |
| AI Model | `assets/face_landmarker.task` |
| Logs | Console output |
