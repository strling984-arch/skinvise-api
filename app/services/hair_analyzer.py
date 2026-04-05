"""Hair analysis service using OpenCV image processing."""

import cv2
import numpy as np
from dataclasses import dataclass

MEDICAL_SEVERITY_THRESHOLD = 85

@dataclass
class HairAnalysis:
    """Result of hair analysis."""
    hair_type: str       # "Straight", "Wavy", "Curly", "Coily"
    frizz: int           # 0-100
    dullness: int        # 0-100
    flatness: int        # 0-100
    concerns: list[str]  # ["frizz", "dullness", "flatness", "damage"]
    concern_severities: dict[str, int]
    flagged_medical: bool
    medical_note: str | None = None


def _analyze_frizz(hair_gray: np.ndarray) -> int:
    """Detect frizz by calculating high frequency edges (Laplacian variance)."""
    laplacian = cv2.Laplacian(hair_gray, cv2.CV_64F)
    variance = laplacian.var()
    # High variance usually indicates textured or frizzy hair 
    frizz = int(min(100, (variance / 8)))
    return frizz


def _analyze_dullness(hair_hsv: np.ndarray) -> int:
    """Detect dullness by evaluating brightness and shine (Value channel)."""
    h, s, v = cv2.split(hair_hsv)
    mean_v = float(np.mean(v))
    # Shiny hair has higher brightness spots.
    dullness = int(max(0, 100 - (mean_v * 0.8)))
    return dullness


def analyze_hair(hair_roi: np.ndarray) -> HairAnalysis:
    """
    Full hair analysis pipeline on a hair ROI image.
    """
    hair_resized = cv2.resize(hair_roi, (256, 256))
    
    hair_hsv = cv2.cvtColor(hair_resized, cv2.COLOR_BGR2HSV)
    hair_gray = cv2.cvtColor(hair_resized, cv2.COLOR_BGR2GRAY)
    
    frizz = _analyze_frizz(hair_gray)
    dullness = _analyze_dullness(hair_hsv)
    flatness = int(max(0, 100 - frizz)) # Flat hair usually has low volume/texture variance
    
    concerns = []
    severities = {}
    
    if frizz > 40:
        concerns.append("frizz")
        severities["frizz"] = frizz
        
    if dullness > 50:
        concerns.append("dullness")
        severities["dullness"] = dullness
        
    if flatness > 65:
        concerns.append("flatness")
        severities["flatness"] = flatness
        
    if frizz > 75 and dullness > 60:
        concerns.append("damage")
        severities["damage"] = max(frizz, dullness)
        
    return HairAnalysis(
        hair_type="Wavy", # Mocked basic hair type detection
        frizz=frizz,
        dullness=dullness,
        flatness=flatness,
        concerns=concerns,
        concern_severities=severities,
        flagged_medical=False,
        medical_note=None
    )
