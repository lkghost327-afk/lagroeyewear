# 🍎 LagroEyecare — macOS Distribution

## Prerequisites

- **Python 3.10+** (install via [Homebrew](https://brew.sh): `brew install python`)
- **pip** package manager
- A webcam
- Camera permissions granted in **System Preferences → Privacy & Security → Camera**

## Quick Start (Run from Source)

```bash
# 1. Install dependencies
pip3 install -r requirements.txt

# 2. Download the FaceLandmarker model (required, ~4 MB)
curl -L -o assets/face_landmarker.task \
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"

# 3. Run the app
python3 main.py
```

## Build macOS Application (.app)

To create a standalone `LagroEyecare.app` bundle:

### Option 1: Use the Build Script

```bash
# Make the script executable and run it:
chmod +x build.sh
./build.sh
```

The build script will:
1. Install Python dependencies
2. Install PyInstaller
3. Download the FaceLandmarker model (if not present)
4. Build the .app bundle

### Option 2: Manual Build with PyInstaller

```bash
# 1. Install PyInstaller
pip3 install pyinstaller

# 2. Download the model (if not present)
curl -L -o assets/face_landmarker.task \
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"

# 3. Build the .app bundle
cd ..
pyinstaller \
    --name "LagroEyecare" \
    --onefile \
    --windowed \
    --icon assets/icon.png \
    --add-data "assets/icon.png:assets" \
    --add-data "assets/face_landmarker.task:assets" \
    --hidden-import mediapipe \
    --hidden-import mediapipe.tasks \
    --hidden-import mediapipe.tasks.python \
    --hidden-import mediapipe.tasks.python.vision \
    --hidden-import mediapipe.tasks.python.vision.face_landmarker \
    --hidden-import customtkinter \
    --hidden-import pystray \
    --hidden-import pystray._darwin \
    --hidden-import plyer \
    --hidden-import plyer.platforms.macosx.notification \
    --hidden-import PIL \
    --hidden-import PIL.Image \
    --hidden-import PIL.ImageDraw \
    --hidden-import PIL.ImageTk \
    --hidden-import matplotlib.backends.backend_tkagg \
    --noconfirm \
    main.py

# 4. Find the app bundle
# The .app will be in: dist/LagroEyecare.app
```

### Option 3: Build with py2app (Native macOS)

```bash
# 1. Install py2app
pip3 install py2app

# 2. Build using the setup file
python3 setup_mac.py py2app

# 3. Find the .app in dist/
```

## Auto-Start on Login

LagroEyecare can automatically start when you log in:

1. Open the app
2. Click **Settings** (⚙ gear icon)
3. Toggle **"Start with System"** ON

This creates a LaunchAgent at:
```
~/Library/LaunchAgents/com.lagroeyecare.app.plist
```

To disable, toggle it OFF in Settings, or manually delete the plist:
```bash
rm ~/Library/LaunchAgents/com.lagroeyecare.app.plist
```

## System Tray (Menu Bar)

- The app adds an icon to the macOS menu bar
- Click the icon for quick actions (Force Break, Pause, Quit)
- Closing the window minimizes to the menu bar

## Camera Permissions

macOS requires explicit camera access. If prompted:

1. Click **Allow** when the system asks for camera access
2. If denied, go to **System Preferences → Privacy & Security → Camera**
3. Enable camera access for **Python** or **LagroEyecare**

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Camera not working | Grant camera permissions in System Preferences |
| App won't open | Right-click → Open (first launch Gatekeeper bypass) |
| tkinter not found | `brew install python-tk` |
| MediaPipe errors | `pip3 install mediapipe --upgrade` |
| Build fails | Ensure Xcode Command Line Tools: `xcode-select --install` |
| Model not found | Download `face_landmarker.task` and place in `assets/` |
