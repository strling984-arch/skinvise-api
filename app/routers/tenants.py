"""Tenant/store management endpoints."""

import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import hash_api_key, get_current_tenant
from app.models.db_models import Tenant, Product, AnalysisHistory
from app.schemas.schemas import TenantCreate, TenantResponse, TenantInfo, AnalysisHistoryResponse, MessageResponse

router = APIRouter(prefix="/v1/tenants", tags=["Tenants"])


@router.post(
    "",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new store/tenant",
    description="Creates a new tenant and returns their API key. Save this key — it cannot be retrieved later.",
)
async def create_tenant(
    tenant_data: TenantCreate,
    db: AsyncSession = Depends(get_db),
) -> TenantResponse:
    # Check for duplicate email
    existing = await db.execute(
        select(Tenant).where(Tenant.email == tenant_data.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A tenant with this email already exists.",
        )

    # Generate API key
    raw_api_key = f"sv_{secrets.token_urlsafe(32)}"
    hashed_key = hash_api_key(raw_api_key)

    # Create tenant
    tenant = Tenant(
        name=tenant_data.name,
        email=tenant_data.email,
        domain=tenant_data.domain,
        api_key_hash=hashed_key,
    )
    db.add(tenant)
    await db.flush()
    await db.refresh(tenant)

    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        email=tenant.email,
        domain=tenant.domain,
        is_active=tenant.is_active,
        created_at=tenant.created_at,
        api_key=raw_api_key,  # Only returned on creation!
    )


@router.get(
    "/me",
    response_model=TenantInfo,
    summary="Get current tenant info",
    description="Returns info about the authenticated tenant, including product and analysis counts.",
)
async def get_tenant_info(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> TenantInfo:
    # Count products
    product_count_result = await db.execute(
        select(func.count(Product.id)).where(Product.tenant_id == tenant.id)
    )
    product_count = product_count_result.scalar() or 0

    # Count analyses
    analysis_count_result = await db.execute(
        select(func.count(AnalysisHistory.id)).where(AnalysisHistory.tenant_id == tenant.id)
    )
    analysis_count = analysis_count_result.scalar() or 0

    return TenantInfo(
        id=tenant.id,
        name=tenant.name,
        email=tenant.email,
        domain=tenant.domain,
        is_active=tenant.is_active,
        created_at=tenant.created_at,
        product_count=product_count,
        analysis_count=analysis_count,
    )


@router.get(
    "/me/history",
    response_model=list[AnalysisHistoryResponse],
    summary="Get analysis history",
    description="Returns past skin analyses for the authenticated tenant, most recent first.",
)
async def get_analysis_history(
    limit: int = 50,
    offset: int = 0,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> list[AnalysisHistoryResponse]:
    result = await db.execute(
        select(AnalysisHistory)
        .where(AnalysisHistory.tenant_id == tenant.id)
        .order_by(AnalysisHistory.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    analyses = result.scalars().all()
    return [AnalysisHistoryResponse.model_validate(a) for a in analyses]


@router.post(
    "/me/regenerate-key",
    response_model=TenantResponse,
    summary="Regenerate API key",
    description="Generates a new API key and invalidates the old one.",
)
async def regenerate_api_key(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> TenantResponse:
    raw_api_key = f"sv_{secrets.token_urlsafe(32)}"
    tenant.api_key_hash = hash_api_key(raw_api_key)
    await db.flush()
    await db.refresh(tenant)

    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        email=tenant.email,
        domain=tenant.domain,
        is_active=tenant.is_active,
        created_at=tenant.created_at,
        api_key=raw_api_key,
    )
