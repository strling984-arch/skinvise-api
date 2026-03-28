"""Core endpoint: POST /v1/analyze-skin"""

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_tenant
from app.models.db_models import Tenant, AnalysisHistory
from app.schemas.schemas import SkinAnalysisResponse, SkinAnalysisResult, SkinScores, ProductRecommendation
from app.services.image_validator import validate_image
from app.services.skin_analyzer import analyze_skin
from app.services.product_matcher import match_products
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/v1", tags=["Skin Analysis"])


@router.post(
    "/analyze-skin",
    response_model=SkinAnalysisResponse,
    summary="Analyze skin from a face photo",
    description=(
        "Upload a face photo to receive skin type analysis, scores, "
        "concern detection, and product recommendations from your catalog."
    ),
)
async def analyze_skin_endpoint(
    image: UploadFile = File(..., description="Face photo (JPEG/PNG)"),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> SkinAnalysisResponse:
    """
    Main analysis pipeline:
    1. Validate image (face detection, brightness, sharpness)
    2. Analyze skin (type, scores, concerns)
    3. Match products from tenant's catalog
    4. Log analysis to history
    5. Return results
    """
    # Validate file type
    if image.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Please upload a JPEG, PNG, or WebP image.",
        )

    # Check file size
    contents = await image.read()
    max_bytes = settings.MAX_IMAGE_SIZE_MB * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image too large. Maximum size is {settings.MAX_IMAGE_SIZE_MB}MB.",
        )

    # Step 1: Validate image (face detection, quality checks)
    validation = validate_image(contents)

    # Step 2: Analyze skin
    analysis = analyze_skin(validation.face_roi)

    # Step 3: Match products
    recommendations_data = await match_products(db, tenant.id, analysis)

    # Build response
    recommendations = [
        ProductRecommendation(**rec) for rec in recommendations_data
    ]

    response = SkinAnalysisResponse(
        analysis=SkinAnalysisResult(
            skin_type=analysis.skin_type,
            score=SkinScores(
                hydration=analysis.hydration,
                oiliness=analysis.oiliness,
                clarity=analysis.clarity,
            ),
            concerns=analysis.concerns,
            concern_severities=analysis.concern_severities,
        ),
        recommendations=recommendations,
        flagged_medical=analysis.flagged_medical,
        medical_note=analysis.medical_note,
    )

    # Step 4: Log to history
    history_entry = AnalysisHistory(
        tenant_id=tenant.id,
        skin_type=analysis.skin_type,
        scores={
            "hydration": analysis.hydration,
            "oiliness": analysis.oiliness,
            "clarity": analysis.clarity,
        },
        concerns=analysis.concerns,
        recommendations=recommendations_data,
        flagged_medical=analysis.flagged_medical,
    )
    db.add(history_entry)
    await db.flush()

    return response
