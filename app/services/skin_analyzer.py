"""Skin analysis service using OpenCV image processing."""

import cv2
import numpy as np
from dataclasses import dataclass


# ─── Skin concern thresholds ─────────────────────────────────────

MEDICAL_SEVERITY_THRESHOLD = 85  # Score above this triggers medical flag

SKIN_TYPE_LABELS = {
    "oily": "Oily",
    "dry": "Dry",
    "combination": "Combination",
    "normal": "Normal",
}

ROUTINE_STEPS = ["Cleanse", "Tone", "Treat", "Moisturize", "Protect"]


@dataclass
class SkinAnalysis:
    """Result of skin analysis."""
    skin_type: str       # "Oily", "Dry", "Combination", "Normal"
    hydration: int       # 0-100
    oiliness: int        # 0-100
    clarity: int         # 0-100
    concerns: list[str]  # ["acne", "pores", "oiliness", ...]
    concern_severities: dict[str, int]  # {"acne": 85, "pigmentation": 30...}
    flagged_medical: bool
    medical_note: str | None = None


def _analyze_skin_type(face_hsv: np.ndarray) -> tuple[str, int, int]:
    """
    Analyze skin type from HSV channels.
    Returns (skin_type, oiliness_score, hydration_score).
    """
    h, s, v = cv2.split(face_hsv)

    # Oiliness: high value (brightness/shininess) + high saturation in certain regions
    mean_v = float(np.mean(v))
    std_v = float(np.std(v))
    mean_s = float(np.mean(s))

    # Shiny spots indicate oiliness (high brightness variance)
    highlight_mask = v > (mean_v + std_v * 1.2)
    shiny_ratio = float(np.sum(highlight_mask)) / float(v.size) * 100

    # Oiliness score (0-100)
    oiliness = int(min(100, max(0, shiny_ratio * 5 + mean_v * 0.2)))

    # Hydration: based on saturation (well-hydrated skin has moderate, even saturation)
    saturation_evenness = 100 - min(100, float(np.std(s)) * 2)
    hydration = int(min(100, max(0, mean_s * 0.5 + saturation_evenness * 0.5)))

    # Classify skin type
    if oiliness > 65:
        if hydration < 40:
            skin_type = "Combination"
        else:
            skin_type = "Oily"
    elif hydration < 35:
        skin_type = "Dry"
    else:
        skin_type = "Normal"

    return skin_type, oiliness, hydration


def _analyze_clarity(face_gray: np.ndarray) -> tuple[int, list[str], dict[str, int]]:
    """
    Analyze skin clarity and detect concerns.
    Returns (clarity_score, list_of_concerns, concern_severities).
    """
    concerns = []
    severities = {}

    blur = cv2.GaussianBlur(face_gray, (5, 5), 0)
    adaptive = cv2.adaptiveThreshold(
        blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
    )

    contours, _ = cv2.findContours(adaptive, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    significant_spots = [c for c in contours if 20 < cv2.contourArea(c) < 500]
    spot_count = len(significant_spots)

    large_spots = [c for c in contours if cv2.contourArea(c) > 200]
    acne_count = len(large_spots)

    if acne_count > 5:
        concerns.append("acne")
        severities["acne"] = min(100, acne_count * 5)
    else:
        severities["acne"] = min(100, acne_count * 2)

    if spot_count > 30:
        concerns.append("pores")
        severities["pores"] = min(100, spot_count)
    else:
        severities["pores"] = min(100, spot_count * 2)

    clarity = int(max(0, min(100, 100 - spot_count * 1.5)))

    return clarity, concerns, severities


def _detect_pigmentation(face_lab: np.ndarray) -> tuple[bool, int]:
    """Detect pigmentation/dark spots. Returns (has_pigmentation, severity_score)."""
    l_channel = face_lab[:, :, 0]

    mean_l = np.mean(l_channel)
    dark_mask = l_channel < (mean_l - 30)
    dark_ratio = float(np.sum(dark_mask)) / float(l_channel.size)

    severity = int(min(100, dark_ratio * 1000))
    return dark_ratio > 0.08, severity


def _detect_redness(face_hsv: np.ndarray) -> tuple[bool, int]:
    """Detect skin redness/irritation. Returns (has_redness, severity_score)."""
    h, s, v = cv2.split(face_hsv)

    red_mask_low = (h < 10) & (s > 50)
    red_mask_high = (h > 170) & (s > 50)
    red_mask = red_mask_low | red_mask_high

    red_ratio = float(np.sum(red_mask)) / float(h.size)
    severity = int(min(100, red_ratio * 800))
    return red_ratio > 0.15, severity


def analyze_skin(face_roi: np.ndarray) -> SkinAnalysis:
    """
    Full skin analysis pipeline on a face ROI image.

    Steps:
    1. Convert to multiple color spaces (HSV, LAB, Gray)
    2. Analyze skin type (oily/dry/combination/normal)
    3. Analyze clarity (blemishes, pores)
    4. Detect specific concerns (pigmentation, redness)
    5. Check medical severity threshold

    Args:
        face_roi: BGR image of the face region

    Returns:
        SkinAnalysis dataclass with all results
    """
    # Resize for consistent analysis
    face_resized = cv2.resize(face_roi, (256, 256))

    # Convert color spaces
    face_hsv = cv2.cvtColor(face_resized, cv2.COLOR_BGR2HSV)
    face_lab = cv2.cvtColor(face_resized, cv2.COLOR_BGR2LAB)
    face_gray = cv2.cvtColor(face_resized, cv2.COLOR_BGR2GRAY)

    # 1. Skin type analysis
    skin_type, oiliness, hydration = _analyze_skin_type(face_hsv)

    # 2. Clarity analysis
    clarity, concerns, severities = _analyze_clarity(face_gray)

    # 3. Pigmentation detection
    has_pigmentation, pig_severity = _detect_pigmentation(face_lab)
    severities["pigmentation"] = pig_severity
    if has_pigmentation:
        concerns.append("pigmentation")

    # 4. Redness detection
    has_redness, red_severity = _detect_redness(face_hsv)
    severities["redness"] = red_severity
    if has_redness:
        concerns.append("redness")

    # 5. Add concerns based on scores
    if oiliness > 70:
        concerns.append("oiliness")
    severities["oiliness"] = oiliness

    if hydration < 30:
        concerns.append("dryness")
    severities["dryness"] = max(0, 100 - hydration)

    # Deduplicate
    concerns = list(set(concerns))

    # 6. Medical flag check
    severity_score = len(concerns) * 15 + max(severities.values()) * 0.5
    flagged_medical = severity_score > MEDICAL_SEVERITY_THRESHOLD
    medical_note = None
    if flagged_medical:
        medical_note = (
            "⚠️ Our analysis detected signs that may indicate a skin condition "
            "requiring professional attention. We recommend consulting a dermatologist "
            "for a proper diagnosis."
        )

    return SkinAnalysis(
        skin_type=skin_type,
        hydration=hydration,
        oiliness=oiliness,
        clarity=clarity,
        concerns=concerns,
        concern_severities=severities,
        flagged_medical=flagged_medical,
        medical_note=medical_note,
    )
