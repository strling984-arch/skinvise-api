"""Body skin analysis service."""

# Body skin analysis uses the exact same visual heuristics (HSV, LAB thresholds)
# as facial skin analysis to detect redness, keratosis (spots), dryness and oiliness.
from app.services.skin_analyzer import analyze_skin, SkinAnalysis

# Alias the function for explicit router usage
analyze_body = analyze_skin
BodyAnalysis = SkinAnalysis
