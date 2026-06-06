<div align="center">

# 👁️ LagroEyewear

### AI-Powered Eye Health & Blink Rate Monitor

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.x-orange.svg)](https://opencv.org)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-Latest-red.svg)](https://mediapipe.dev)

*Protect your eyes from digital strain with real-time AI-powered blink monitoring*

</div>

---

## 🔍 What is LagroEyewear?

LagroEyewear is a desktop application that uses your webcam and computer vision (MediaPipe Face Landmarker) to monitor your blink rate in real time. When it detects you're not blinking enough — a key sign of digital eye strain — it alerts you and helps you take breaks.

### ✨ Key Features

- **Real-Time Blink Detection** — Uses MediaPipe Face Landmarker with Eye Aspect Ratio (EAR) algorithm
- **Smart Break Reminders** — Implements the 20-20-20 rule automatically
- **Screen Blur Overlay** — Forces eye rest with a fullscreen frosted overlay
- **Eye Strain Scoring** — Tracks your eye health over time (0-100 score)
- **Desktop Notifications** — Alerts you when blink rate drops too low
- **System Tray Integration** — Runs quietly in the background
- **Auto-Start on Boot** — Optionally launch with your OS (Windows & macOS)
- **Dark Mode Dashboard** — Beautiful, modern UI with live stats and charts
- **Session History** — SQLite database tracks all your eye health data
- **Cross-Platform** — Runs on Windows and macOS with build scripts for both

## 📸 Screenshots

*Main dashboard with live webcam feed, blink rate stats, and break countdown*
![LagroEyewear Dashboard](assets/screenshot1.png)

![LagroEyewear Break Overlay](assets/screenshot2.png)
## 🧠 How It Works

### Eye Aspect Ratio (EAR)

The app tracks 6 landmarks around each eye using MediaPipe's 478-point face mesh:

```
EAR = (|p2-p6| + |p3-p5|) / (2 × |p1-p4|)
```

When you blink, the EAR drops sharply below 0.25. By tracking this across consecutive frames, the app accurately detects each blink.

- **Normal blink rate**: 15-20 blinks/minute
- **Low blink alert**: Below 12 blinks/minute for 60+ seconds

### Eye Strain Score (0-100)

- Starts at 100 (perfect)
- -2 points per minute with low blink rate
- -1 point per 10 minutes without a break
- +5 points for each completed break

## 🚀 Quick Start

### Prerequisites
- Python 3.10 or higher
- Webcam

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/LagroEyewear.git
cd LagroEyewear

# Install dependencies
pip install -r requirements.txt

# Download the FaceLandmarker AI model (~4 MB)
# Windows (PowerShell):
Invoke-WebRequest -Uri "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task" -OutFile "assets/face_landmarker.task"

# macOS/Linux:
curl -L -o assets/face_landmarker.task "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"

# Run the app
python main.py
```

### Build Executable

**Windows** — Creates `LagroEyecare.exe`:
```bash
cd Windows
build.bat
```

**macOS** — Creates `LagroEyecare.app`:
```bash
cd macOS
chmod +x build.sh
./build.sh
```

See [Windows/README.md](Windows/README.md) and [macOS/README.md](macOS/README.md) for detailed platform instructions.

## 📁 Project Structure

```
lagroeyewear/
├── main.py                          # Entry point
├── requirements.txt                 # Dependencies
├── lagroeyecare.spec                # PyInstaller build spec
├── core/
│   ├── blink_detector.py            # MediaPipe FaceLandmarker blink detection
│   ├── session_manager.py           # Session tracking & eye strain scoring
│   └── database.py                  # SQLite database operations
├── ui/
│   ├── main_window.py               # Main 3-column dashboard GUI
│   ├── overlay.py                   # Fullscreen break overlay
│   ├── tray.py                      # System tray integration
│   └── components.py                # Reusable UI widgets
├── utils/
│   ├── notifications.py             # Desktop notification system
│   ├── settings.py                  # JSON settings persistence
│   └── autostart.py                 # OS auto-start management
├── assets/
│   ├── icon.png                     # App icon
│   └── face_landmarker.task         # MediaPipe AI model (download required)
├── data/
│   └── lagroeyewear.db              # SQLite database (auto-created)
├── Windows/
│   ├── build.bat                    # Windows build script
│   ├── lagroeyecare.spec            # PyInstaller spec
│   └── README.md                    # Windows instructions
└── macOS/
    ├── build.sh                     # macOS build script
    ├── setup_mac.py                 # py2app setup
    └── README.md                    # macOS instructions
```

## ⚙️ Configuration

Settings are saved to `settings.json` and persist across sessions:

| Setting | Default | Range |
|---------|---------|-------|
| Break Interval | 20 min | 10-60 min |
| Break Duration | 20 sec | — |
| Low Blink Threshold | 12 bpm | 5-20 bpm |
| Notifications | Enabled | On/Off |
| Start Minimized | Disabled | On/Off |
| Start with System | Disabled | On/Off |

## 🛠️ Tech Stack

- **Computer Vision**: OpenCV + MediaPipe Face Landmarker (Tasks API)
- **GUI**: CustomTkinter (modern dark-mode)
- **Charts**: Matplotlib
- **Database**: SQLite3
- **Notifications**: Plyer
- **System Tray**: Pystray + Pillow

## 📋 The 20-20-20 Rule

Every **20** minutes, look at something **20** feet away for **20** seconds. LagroEyewear automates this rule and also triggers emergency breaks when your blink rate drops dangerously low.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👤 Author

Made with ❤️ for healthier eyes

---

<div align="center">

**⭐ Star this repo if you find it useful!**

</div>
