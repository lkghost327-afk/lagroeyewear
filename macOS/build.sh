#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
#  LagroEyecare — macOS Build Script
#  Creates a standalone .app bundle using PyInstaller
# ═══════════════════════════════════════════════════════════════════════════

set -e

echo ""
echo "  ========================================"
echo "   LagroEyecare - macOS Build"
echo "  ========================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed."
    echo "Install via Homebrew: brew install python"
    exit 1
fi

echo "[1/4] Installing dependencies..."
pip3 install -r ../requirements.txt

echo "[2/4] Installing PyInstaller..."
pip3 install pyinstaller

echo "[3/4] Checking FaceLandmarker model..."
if [ ! -f "../assets/face_landmarker.task" ]; then
    echo "Downloading face_landmarker.task model..."
    curl -L -o "../assets/face_landmarker.task" \
        "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
    echo "Model downloaded successfully."
else
    echo "Model already present."
fi

echo "[4/4] Building LagroEyecare.app..."
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
    --hidden-import mediapipe.tasks.python.core \
    --hidden-import mediapipe.tasks.python.core.task_runner \
    --hidden-import mediapipe.tasks.python.components \
    --hidden-import mediapipe.tasks.python.components.containers \
    --hidden-import customtkinter \
    --hidden-import pystray \
    --hidden-import "pystray._darwin" \
    --hidden-import plyer \
    --hidden-import "plyer.platforms.macosx.notification" \
    --hidden-import PIL \
    --hidden-import PIL.Image \
    --hidden-import PIL.ImageDraw \
    --hidden-import PIL.ImageTk \
    --hidden-import "matplotlib.backends.backend_tkagg" \
    --noconfirm \
    main.py

echo ""
echo "  ========================================"
echo "   BUILD COMPLETE!"
echo "  ========================================"
echo ""
echo "  App bundle: dist/LagroEyecare"
echo "  You can now move it to /Applications!"
echo ""
