"""
SpecGen AI — Video Processor Service
Extracts meaningful keyframes from screen recordings using OpenCV and SSIM.
Only captures frames where the UI actually changed (visual state transitions).
"""

import cv2
import base64
import tempfile
import os
import logging
from pathlib import Path
from skimage.metrics import structural_similarity as ssim

logger = logging.getLogger(__name__)

# --- Configuration ---
SSIM_THRESHOLD = 0.85       # Below this = meaningful UI change detected
SAMPLE_FPS = 1              # Process 1 frame per second (saves compute)
MAX_KEYFRAMES = 20          # Hard cap to control API costs
MAX_VIDEO_DURATION = 120    # 2 minutes max
MIN_KEYFRAMES = 2           # Minimum frames needed for useful output
RESIZE_WIDTH = 1024         # Resize frames for consistent processing


class VideoProcessingError(Exception):
    """Raised when video processing fails."""
    pass


def _resize_frame(frame, width=RESIZE_WIDTH):
    """Resize frame maintaining aspect ratio."""
    h, w = frame.shape[:2]
    ratio = width / w
    new_h = int(h * ratio)
    return cv2.resize(frame, (width, new_h), interpolation=cv2.INTER_AREA)


def _frame_to_base64(frame) -> str:
    """Encode an OpenCV frame as base64 JPEG string."""
    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return base64.b64encode(buffer).decode('utf-8')


def _validate_video(cap: cv2.VideoCapture) -> tuple[float, float, int]:
    """Validate video properties and return (fps, duration, total_frames)."""
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if fps <= 0 or total_frames <= 0:
        raise VideoProcessingError(
            "Could not read video properties. File may be corrupted or unsupported."
        )

    duration = total_frames / fps

    if duration > MAX_VIDEO_DURATION:
        raise VideoProcessingError(
            f"Video is {duration:.0f}s long. Maximum allowed is {MAX_VIDEO_DURATION}s. "
            f"Please record a focused walkthrough under 2 minutes."
        )

    if duration < 2:
        raise VideoProcessingError(
            "Video is too short. Please upload at least a 2-second recording."
        )

    return fps, duration, total_frames


def extract_keyframes(video_path: str, threshold: float = SSIM_THRESHOLD) -> list[dict]:
    """
    Extract keyframes from a video where meaningful UI changes occur.

    Uses Structural Similarity Index (SSIM) to compare consecutive frames.
    When SSIM drops below the threshold, it means the UI changed significantly
    (page navigation, modal open, form submission, etc.).

    Args:
        video_path: Path to the video file (MP4/WEBM)
        threshold: SSIM threshold (lower = less sensitive to changes)

    Returns:
        List of dicts with 'base64' (image data), 'timestamp' (seconds),
        and 'frame_index' (position in video)
    """
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        raise VideoProcessingError(
            "Could not open video file. Supported formats: MP4, WEBM."
        )

    try:
        fps, duration, total_frames = _validate_video(cap)
        frame_interval = max(1, int(fps / SAMPLE_FPS))  # Sample at 1 FPS

        logger.info(
            f"Processing video: {duration:.1f}s, {fps:.0f}fps, "
            f"sampling every {frame_interval} frames"
        )

        keyframes = []
        prev_gray = None
        frame_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Only process at our target sample rate
            if frame_count % frame_interval != 0:
                frame_count += 1
                continue

            # Resize for consistent comparison
            resized = _resize_frame(frame)
            gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

            timestamp = frame_count / fps

            if prev_gray is None:
                # Always capture the first frame
                keyframes.append({
                    'base64': _frame_to_base64(resized),
                    'timestamp': round(timestamp, 1),
                    'frame_index': frame_count,
                    'ssim_score': None,
                    'description': f"Initial state at {timestamp:.1f}s"
                })
                prev_gray = gray
                frame_count += 1
                continue

            # Compare with previous frame using SSIM
            score = ssim(prev_gray, gray)

            if score < threshold:
                keyframes.append({
                    'base64': _frame_to_base64(resized),
                    'timestamp': round(timestamp, 1),
                    'frame_index': frame_count,
                    'ssim_score': round(score, 4),
                    'description': f"UI change detected at {timestamp:.1f}s (SSIM: {score:.4f})"
                })
                prev_gray = gray
                logger.debug(f"Keyframe at {timestamp:.1f}s — SSIM: {score:.4f}")

            # Stop if we hit the max
            if len(keyframes) >= MAX_KEYFRAMES:
                logger.warning(
                    f"Hit max keyframes ({MAX_KEYFRAMES}). "
                    f"Video may have too many transitions."
                )
                break

            frame_count += 1

        # Always capture the last frame if it's different from what we have
        if keyframes and frame_count > 0:
            cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames - 1)
            ret, last_frame = cap.read()
            if ret:
                last_resized = _resize_frame(last_frame)
                last_gray = cv2.cvtColor(last_resized, cv2.COLOR_BGR2GRAY)
                last_score = ssim(prev_gray, last_gray)
                if last_score < threshold:
                    keyframes.append({
                        'base64': _frame_to_base64(last_resized),
                        'timestamp': round(duration, 1),
                        'frame_index': total_frames - 1,
                        'ssim_score': round(last_score, 4),
                        'description': f"Final state at {duration:.1f}s"
                    })

        if len(keyframes) < MIN_KEYFRAMES:
            raise VideoProcessingError(
                f"Only {len(keyframes)} keyframe(s) detected. The video may be "
                f"too static or too short. Try recording a walkthrough with "
                f"more visible UI interactions."
            )

        logger.info(f"Extracted {len(keyframes)} keyframes from {duration:.1f}s video")
        return keyframes

    finally:
        cap.release()


def get_video_info(video_path: str) -> dict:
    """Get basic video metadata without full processing."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise VideoProcessingError("Could not open video file.")

    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = total_frames / fps if fps > 0 else 0

        return {
            'fps': round(fps, 1),
            'duration': round(duration, 1),
            'total_frames': total_frames,
            'resolution': f"{width}x{height}",
            'estimated_keyframes': f"{MIN_KEYFRAMES}-{MAX_KEYFRAMES}"
        }
    finally:
        cap.release()
