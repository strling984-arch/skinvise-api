"""Image validation service using OpenCV."""

import cv2
import numpy as np
from fastapi import HTTPException, status
from app.config import get_settings


settings = get_settings()


class ImageValidationResult:
    """Result of image validation."""

    def __init__(self, face_roi: np.ndarray, full_image: np.ndarray, brightness: float, sharpness: float):
        self.face_roi = face_roi
        self.full_image = full_image
        self.brightness = brightness
        self.sharpness = sharpness


def _check_brightness(image: np.ndarray) -> float:
    """Calculate average brightness of an image (0-255)."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    return float(np.mean(gray))


def _check_sharpness(image: np.ndarray) -> float:
    """Calculate sharpness using Laplacian variance. Higher = sharper."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _detect_face(image: np.ndarray) -> tuple[int, int, int, int] | None:
    """
    Detect a face using OpenCV Haar Cascade.
    Returns (x, y, w, h) of the largest face or None.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Use Haar Cascade for face detection
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(80, 80),
    )

    if len(faces) == 0:
        return None

    # Return the largest face
    faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
    return tuple(faces[0])


def validate_image(image_bytes: bytes) -> ImageValidationResult:
    """
    Validate an uploaded image:
    1. Decode the image
    2. Check brightness
    3. Check sharpness (blur detection)
    4. Detect face presence

    Returns ImageValidationResult with face ROI, or raises HTTPException.
    """
    # 1. Decode image
    nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if image is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image file. Could not decode the image.",
        )

    # 2. Check brightness
    brightness = _check_brightness(image)
    if brightness < settings.MIN_BRIGHTNESS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Image is too dark (brightness: {brightness:.0f}). Please use better lighting.",
        )
    if brightness > settings.MAX_BRIGHTNESS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Image is too bright/overexposed (brightness: {brightness:.0f}). Please reduce lighting.",
        )

    # 3. Check sharpness
    sharpness = _check_sharpness(image)
    if sharpness < settings.MIN_SHARPNESS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Image is too blurry (sharpness: {sharpness:.0f}). Please hold the camera steady.",
        )

    # 4. Detect face
    face_rect = _detect_face(image)
    if face_rect is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No face detected in the image. Please upload a clear face photo.",
        )

    x, y, w, h = face_rect

    # Add padding around face (30% extra on each side)
    pad_w = int(w * 0.3)
    pad_h = int(h * 0.3)
    x1 = max(0, x - pad_w)
    y1 = max(0, y - pad_h)
    x2 = min(image.shape[1], x + w + pad_w)
    y2 = min(image.shape[0], y + h + pad_h)

    face_roi = image[y1:y2, x1:x2]

    return ImageValidationResult(
        face_roi=face_roi,
        full_image=image,
        brightness=brightness,
        sharpness=sharpness,
    )
