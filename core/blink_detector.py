"""
LagroEyewear Blink Detector Module
===================================

Real-time blink detection using OpenCV and MediaPipe Face Landmarker
(Tasks API).  Calculates the Eye Aspect Ratio (EAR) to identify blinks
and maintains a rolling 60-second window for blinks-per-minute computation.

The detection loop runs in a daemon thread to avoid blocking the UI.
Processed frames with drawn eye landmarks are available for display.

NOTE: This module uses the **new** MediaPipe Tasks vision API
      (`mp.tasks.vision.FaceLandmarker`) which replaced the deprecated
      `mp.solutions.face_mesh`.  It requires a `.task` model bundle file
      located in the `assets/` directory.
"""

import os
import sys
import threading
import time
from collections import deque
from typing import Deque, List, Optional, Tuple

import cv2
import numpy as np

# ─── MediaPipe Tasks imports ───────────────────────────────────────────────
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    FaceLandmarker,
    FaceLandmarkerOptions,
    RunningMode,
)

# ─── Accent colour (BGR for OpenCV) ────────────────────────────────────────
ACCENT_BLUE_BGR: Tuple[int, int, int] = (0xFF, 0x90, 0x4A)  # #4A90FF in BGR
IRIS_COLOR_BGR: Tuple[int, int, int] = (0xA0, 0xE5, 0x00)   # Subtle green-cyan

# ─── Landmark indices (same numbering as the legacy Face Mesh 478 model) ───
LEFT_EYE_INDICES: List[int] = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_INDICES: List[int] = [362, 385, 387, 263, 373, 380]

# Iris contour indices (refined landmarks — available when
# FaceLandmarkerOptions output_face_blendshapes=False by default)
LEFT_IRIS_INDICES: List[int] = [468, 469, 470, 471, 472]
RIGHT_IRIS_INDICES: List[int] = [473, 474, 475, 476, 477]


def _resolve_model_path() -> str:
    """Locate the ``face_landmarker.task`` model bundle.

    Checks several locations in order:
      1. PyInstaller ``_MEIPASS`` temp directory (frozen builds).
      2. ``assets/`` directory relative to this file's parent package.
      3. ``assets/`` directory relative to the working directory.

    Returns:
        Absolute path to the model file.

    Raises:
        FileNotFoundError: If the model cannot be found anywhere.
    """
    candidates: List[str] = []

    # 1. PyInstaller bundle
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS  # type: ignore[attr-defined]
        candidates.append(os.path.join(base, 'assets', 'face_landmarker.task'))

    # 2. Relative to this source file's package root
    pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates.append(os.path.join(pkg_root, 'assets', 'face_landmarker.task'))

    # 3. Relative to CWD
    candidates.append(os.path.join(os.getcwd(), 'assets', 'face_landmarker.task'))

    for path in candidates:
        if os.path.isfile(path):
            return path

    raise FileNotFoundError(
        "Could not find 'face_landmarker.task'. "
        "Please download it from:\n"
        "  https://storage.googleapis.com/mediapipe-models/"
        "face_landmarker/face_landmarker/float16/1/face_landmarker.task\n"
        "and place it in the 'assets/' directory."
    )


class BlinkDetector:
    """Detects eye blinks in real time via webcam using MediaPipe FaceLandmarker.

    Uses the Eye Aspect Ratio (EAR) method: when EAR drops below a threshold
    for a minimum number of consecutive frames, a blink is registered.

    Attributes:
        ear_threshold: EAR value below which eyes are considered closed.
        consecutive_frames: Minimum consecutive low-EAR frames to count a blink.
    """

    def __init__(
        self,
        ear_threshold: float = 0.25,
        consecutive_frames: int = 2,
    ) -> None:
        """Initialise the blink detector.

        Args:
            ear_threshold: EAR value below which eyes are considered closed.
            consecutive_frames: Required consecutive sub-threshold frames for a blink.
        """
        # ── Detection parameters ──────────────────────────────────────────
        self.ear_threshold: float = ear_threshold
        self.consecutive_frames: int = consecutive_frames

        # ── MediaPipe FaceLandmarker ──────────────────────────────────────
        model_path = _resolve_model_path()
        options = FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            running_mode=RunningMode.VIDEO,
            num_faces=1,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
        )
        self._landmarker: FaceLandmarker = FaceLandmarker.create_from_options(options)

        # ── State variables ───────────────────────────────────────────────
        self._capture: Optional[cv2.VideoCapture] = None
        self._running: bool = False
        self._thread: Optional[threading.Thread] = None

        # Blink tracking
        self._total_blinks: int = 0
        self._frame_counter: int = 0  # Consecutive low-EAR frame count
        self._blink_timestamps: Deque[float] = deque()  # Rolling 60s window
        self._current_ear: float = 0.0
        self._face_detected: bool = False

        # Monotonically-increasing timestamp for VIDEO mode (ms)
        self._frame_timestamp_ms: int = 0

        # Frame buffer (thread-safe)
        self._current_frame: Optional[np.ndarray] = None
        self._frame_lock: threading.Lock = threading.Lock()

    # ─── Public control methods ────────────────────────────────────────────

    def start(self) -> None:
        """Open the webcam and start the detection loop in a background thread."""
        if self._running:
            return

        self._capture = cv2.VideoCapture(0)
        if not self._capture.isOpened():
            raise RuntimeError("Could not open webcam (index 0).")

        # Set a reasonable capture resolution
        self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        self._running = True
        self._thread = threading.Thread(target=self._detection_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the detection loop, release camera, and close the landmarker."""
        self._running = False

        # Wait for the thread to finish
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

        # Release camera
        if self._capture is not None:
            try:
                self._capture.release()
            except Exception:
                pass
            self._capture = None

        # Close FaceLandmarker
        try:
            self._landmarker.close()
        except Exception:
            pass

    # ─── Detection loop (runs in daemon thread) ───────────────────────────

    def _detection_loop(self) -> None:
        """Main detection loop: reads frames, processes with MediaPipe,
        calculates EAR, detects blinks, and draws landmarks."""
        while self._running:
            if self._capture is None or not self._capture.isOpened():
                time.sleep(0.01)
                continue

            ret, frame = self._capture.read()
            if not ret or frame is None:
                time.sleep(0.01)
                continue

            # Flip horizontally for mirror-view
            frame = cv2.flip(frame, 1)

            # Convert BGR → RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Create a MediaPipe Image
            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=rgb_frame,
            )

            # Advance timestamp monotonically (each frame ~33 ms at 30 fps)
            self._frame_timestamp_ms += 33

            # Run face landmarker
            try:
                results = self._landmarker.detect_for_video(
                    mp_image, self._frame_timestamp_ms
                )
            except Exception:
                time.sleep(0.005)
                continue

            h, w, _ = frame.shape

            if results.face_landmarks and len(results.face_landmarks) > 0:
                self._face_detected = True
                landmarks = results.face_landmarks[0]  # First face

                # ── Calculate EAR for both eyes ──────────────────────────
                left_ear = self._calculate_ear(landmarks, LEFT_EYE_INDICES, (h, w))
                right_ear = self._calculate_ear(landmarks, RIGHT_EYE_INDICES, (h, w))
                avg_ear = (left_ear + right_ear) / 2.0
                self._current_ear = avg_ear

                # ── Blink detection logic ────────────────────────────────
                if avg_ear < self.ear_threshold:
                    self._frame_counter += 1
                else:
                    # If enough consecutive frames were below threshold → blink
                    if self._frame_counter >= self.consecutive_frames:
                        self._total_blinks += 1
                        self._blink_timestamps.append(time.time())
                    self._frame_counter = 0

                # ── Prune blink timestamps outside the 60s window ────────
                cutoff = time.time() - 60.0
                while self._blink_timestamps and self._blink_timestamps[0] < cutoff:
                    self._blink_timestamps.popleft()

                # ── Draw eye landmarks ───────────────────────────────────
                self._draw_eye_landmarks(frame, landmarks, LEFT_EYE_INDICES, (h, w))
                self._draw_eye_landmarks(frame, landmarks, RIGHT_EYE_INDICES, (h, w))

                # ── Draw iris contours subtly (only if enough landmarks) ─
                if len(landmarks) > max(LEFT_IRIS_INDICES + RIGHT_IRIS_INDICES):
                    self._draw_iris_contours(
                        frame, landmarks, LEFT_IRIS_INDICES, (h, w)
                    )
                    self._draw_iris_contours(
                        frame, landmarks, RIGHT_IRIS_INDICES, (h, w)
                    )
            else:
                self._face_detected = False

            # Store the processed frame (thread-safe)
            with self._frame_lock:
                self._current_frame = frame.copy()

            # Small sleep to prevent CPU hogging (~30 FPS cap)
            time.sleep(0.005)

    # ─── EAR calculation ──────────────────────────────────────────────────

    def _calculate_ear(
        self,
        landmarks: list,
        eye_indices: List[int],
        frame_shape: Tuple[int, int],
    ) -> float:
        """Calculate the Eye Aspect Ratio (EAR) for one eye.

        EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)

        Where p1..p6 correspond to the six eye landmark points.

        Args:
            landmarks: MediaPipe NormalizedLandmark list from FaceLandmarker.
            eye_indices: Six landmark indices defining the eye contour.
            frame_shape: (height, width) of the frame for denormalisation.

        Returns:
            The computed EAR value (float).
        """
        h, w = frame_shape

        # Extract (x, y) pixel coordinates for each landmark
        points = np.array(
            [(landmarks[idx].x * w, landmarks[idx].y * h) for idx in eye_indices],
            dtype=np.float64,
        )

        # p1=points[0], p2=points[1], p3=points[2],
        # p4=points[3], p5=points[4], p6=points[5]
        vertical_1 = np.linalg.norm(points[1] - points[5])  # ||p2 - p6||
        vertical_2 = np.linalg.norm(points[2] - points[4])  # ||p3 - p5||
        horizontal = np.linalg.norm(points[0] - points[3])   # ||p1 - p4||

        if horizontal == 0:
            return 0.0

        ear = (vertical_1 + vertical_2) / (2.0 * horizontal)
        return float(ear)

    # ─── Drawing helpers ──────────────────────────────────────────────────

    def _draw_eye_landmarks(
        self,
        frame: np.ndarray,
        landmarks: list,
        eye_indices: List[int],
        frame_shape: Tuple[int, int],
    ) -> None:
        """Draw eye landmarks as blue dots connected by lines.

        Args:
            frame: The BGR image to draw on (modified in-place).
            landmarks: MediaPipe NormalizedLandmark list.
            eye_indices: Six landmark indices defining the eye contour.
            frame_shape: (height, width) of the frame.
        """
        h, w = frame_shape
        pts = [
            (int(landmarks[idx].x * w), int(landmarks[idx].y * h))
            for idx in eye_indices
        ]

        # Draw connecting lines
        for i in range(len(pts)):
            cv2.line(frame, pts[i], pts[(i + 1) % len(pts)], ACCENT_BLUE_BGR, 1, cv2.LINE_AA)

        # Draw landmark dots
        for pt in pts:
            cv2.circle(frame, pt, 2, ACCENT_BLUE_BGR, -1, cv2.LINE_AA)

    def _draw_iris_contours(
        self,
        frame: np.ndarray,
        landmarks: list,
        iris_indices: List[int],
        frame_shape: Tuple[int, int],
    ) -> None:
        """Draw subtle iris contour points.

        Args:
            frame: The BGR image to draw on (modified in-place).
            landmarks: MediaPipe NormalizedLandmark list.
            iris_indices: Landmark indices for one iris.
            frame_shape: (height, width) of the frame.
        """
        h, w = frame_shape
        pts = [
            (int(landmarks[idx].x * w), int(landmarks[idx].y * h))
            for idx in iris_indices
        ]

        # Draw subtle iris circle through the points
        for i in range(len(pts)):
            cv2.line(frame, pts[i], pts[(i + 1) % len(pts)], IRIS_COLOR_BGR, 1, cv2.LINE_AA)

        # Center dot
        if pts:
            cv2.circle(frame, pts[0], 2, IRIS_COLOR_BGR, -1, cv2.LINE_AA)

    # ─── Public getters ───────────────────────────────────────────────────

    def get_frame(self) -> Optional[np.ndarray]:
        """Get the current processed frame with landmarks drawn.

        Returns:
            A copy of the latest BGR frame, or None if unavailable.
        """
        with self._frame_lock:
            if self._current_frame is not None:
                return self._current_frame.copy()
            return None

    def get_blink_rate(self) -> float:
        """Get the current blinks-per-minute from the rolling 60s window.

        Returns:
            Blinks per minute (float). If the window is less than 60 seconds,
            the rate is extrapolated proportionally.
        """
        # Prune old timestamps
        cutoff = time.time() - 60.0
        while self._blink_timestamps and self._blink_timestamps[0] < cutoff:
            self._blink_timestamps.popleft()

        count = len(self._blink_timestamps)
        return float(count)  # Count in last 60s ≈ blinks per minute

    def get_ear(self) -> float:
        """Get the current average Eye Aspect Ratio.

        Returns:
            The most recent average EAR value (float).
        """
        return self._current_ear

    def is_face_detected(self) -> bool:
        """Check whether a face is currently detected in the frame.

        Returns:
            True if a face was found in the last processed frame.
        """
        return self._face_detected

    def is_running(self) -> bool:
        """Check whether the detection loop is active.

        Returns:
            True if the detection loop is currently running.
        """
        return self._running

    def get_total_blinks(self) -> int:
        """Get the total number of blinks detected since start.

        Returns:
            Total blink count (int).
        """
        return self._total_blinks
