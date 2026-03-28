"""Pydantic schemas for request/response validation."""

from datetime import datetime
from pydantic import BaseModel, Field, EmailStr
from typing import Optional


# ─── Skin Analysis ───────────────────────────────────────────────

class SkinScores(BaseModel):
    """Skin analysis scores (0-100)."""
    hydration: int = Field(..., ge=0, le=100, description="Hydration level (0=very dry, 100=very hydrated)")
    oiliness: int = Field(..., ge=0, le=100, description="Oiliness level (0=not oily, 100=very oily)")
    clarity: int = Field(..., ge=0, le=100, description="Skin clarity (0=many blemishes, 100=clear)")


class ProductAlternative(BaseModel):
    """An alternative product recommendation."""
    product_id: str
    product_name: str
    reason: str


class ProductRecommendation(BaseModel):
    """A single product recommendation."""
    step: str = Field(..., description="Skincare routine step", examples=["Cleanse", "Treat", "Moisturize"])
    product_id: str = Field(..., description="Product ID from tenant catalog")
    product_name: str = Field(..., description="Product display name")
    reason: str = Field(..., description="Why this product is recommended")
    alternatives: list[ProductAlternative] = Field(default_factory=list, description="Alternative product choices for this step")


class SkinAnalysisResult(BaseModel):
    """Full skin analysis result."""
    skin_type: str = Field(..., description="Detected skin type", examples=["Oily", "Dry", "Combination", "Normal"])
    score: SkinScores
    concerns: list[str] = Field(default_factory=list, description="Detected skin concerns")
    concern_severities: dict[str, int] = Field(default_factory=dict, description="0-100 severity severity for each concern")


class SkinAnalysisResponse(BaseModel):
    """Top-level API response for skin analysis."""
    analysis: SkinAnalysisResult
    recommendations: list[ProductRecommendation] = Field(default_factory=list)
    flagged_medical: bool = Field(False, description="True if condition may require dermatologist")
    medical_note: Optional[str] = Field(None, description="Medical warning message if flagged")


# ─── Tenant / Store ──────────────────────────────────────────────

class TenantCreate(BaseModel):
    """Request body to register a new tenant."""
    name: str = Field(..., min_length=2, max_length=255, description="Store/business name")
    email: EmailStr = Field(..., description="Contact email")
    domain: Optional[str] = Field(None, max_length=255, description="Store website URL")


class TenantResponse(BaseModel):
    """Tenant info returned after creation."""
    id: str
    name: str
    email: str
    domain: Optional[str]
    is_active: bool
    created_at: datetime
    api_key: Optional[str] = Field(None, description="Returned only on creation (plain text)")

    class Config:
        from_attributes = True


class TenantInfo(BaseModel):
    """Public tenant info (no API key)."""
    id: str
    name: str
    email: str
    domain: Optional[str]
    is_active: bool
    created_at: datetime
    product_count: int = 0
    analysis_count: int = 0

    class Config:
        from_attributes = True


# ─── Products ────────────────────────────────────────────────────

class ProductCreate(BaseModel):
    """Request body to add a product."""
    sku: str = Field(..., min_length=1, max_length=100, description="Product SKU")
    name: str = Field(..., min_length=1, max_length=255, description="Product name")
    category: str = Field(
        ...,
        description="Product category",
        examples=["cleanser", "moisturizer", "serum", "sunscreen", "treatment", "toner", "mask"],
    )
    skin_types: list[str] = Field(
        default_factory=list,
        description="Compatible skin types",
        examples=[["oily", "combination"]],
    )
    concerns: list[str] = Field(
        default_factory=list,
        description="Skin concerns this product addresses",
        examples=[["acne", "pores", "oiliness"]],
    )
    description: Optional[str] = Field(None, description="Product description")
    price: Optional[float] = Field(None, ge=0, description="Product price")
    currency: str = Field("USD", max_length=10)
    image_url: Optional[str] = Field(None, max_length=500)


class ProductResponse(BaseModel):
    """Product returned from API."""
    id: str
    tenant_id: str
    sku: str
    name: str
    category: str
    skin_types: list[str]
    concerns: list[str]
    description: Optional[str]
    price: Optional[float]
    currency: str
    image_url: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ProductImportResult(BaseModel):
    """Result of bulk product import."""
    total_rows: int
    imported: int
    skipped: int
    errors: list[str] = Field(default_factory=list)


# ─── Analysis History ────────────────────────────────────────────

class AnalysisHistoryResponse(BaseModel):
    """A past analysis record."""
    id: str
    skin_type: str
    scores: dict
    concerns: list[str]
    recommendations: list[dict]
    flagged_medical: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Common ──────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    """Generic message response."""
    message: str
    detail: Optional[str] = None
