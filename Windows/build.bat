@echo off
REM ═══════════════════════════════════════════════════════════════════════════
REM  LagroEyecare — Windows Build Script
REM  Creates a standalone .exe using PyInstaller
REM ═══════════════════════════════════════════════════════════════════════════

echo.
echo  ========================================
echo   LagroEyecare - Windows Build
echo  ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not on PATH.
    echo Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

REM Install dependencies
echo [1/4] Installing dependencies...
pip install -r ..\requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

REM Install PyInstaller
echo [2/4] Installing PyInstaller...
pip install pyinstaller
if errorlevel 1 (
    echo [ERROR] Failed to install PyInstaller.
    pause
    exit /b 1
)

REM Download FaceLandmarker model if not present
echo [3/4] Checking FaceLandmarker model...
if not exist "..\assets\face_landmarker.task" (
    echo Downloading face_landmarker.task model...
    powershell -Command "Invoke-WebRequest -Uri 'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task' -OutFile '..\assets\face_landmarker.task'"
    if errorlevel 1 (
        echo [ERROR] Failed to download FaceLandmarker model.
        echo Please download it manually from:
        echo   https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
        echo and place it in the assets\ directory.
        pause
        exit /b 1
    )
    echo Model downloaded successfully.
) else (
    echo Model already present.
)

REM Build the executable
echo [4/4] Building LagroEyecare.exe...
cd ..
pyinstaller lagroeyecare.spec --noconfirm
if errorlevel 1 (
    echo [ERROR] Build failed. Check the error messages above.
    pause
    exit /b 1
)

echo.
echo  ========================================
echo   BUILD COMPLETE!
echo  ========================================
echo.
echo  Executable: dist\LagroEyecare.exe
echo  You can now run LagroEyecare.exe directly!
echo.
pause
