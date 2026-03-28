"""API key authentication middleware."""

from fastapi import Header, HTTPException, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import bcrypt

from app.database import get_db
from app.models.db_models import Tenant


def hash_api_key(api_key: str) -> str:
    """Hash an API key using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(api_key.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """Verify a plain API key against its hash."""
    return bcrypt.checkpw(plain_key.encode('utf-8'), hashed_key.encode('utf-8'))


async def get_current_tenant(
    x_api_key: str = Header(..., description="Tenant API key for authentication"),
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    """
    FastAPI dependency that authenticates a request via X-API-Key header.
    Returns the authenticated Tenant or raises 401.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide X-API-Key header.",
        )

    # Fetch all active tenants and verify against hashed keys
    result = await db.execute(
        select(Tenant).where(Tenant.is_active == True)
    )
    tenants = result.scalars().all()

    for tenant in tenants:
        if verify_api_key(x_api_key, tenant.api_key_hash):
            return tenant

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key.",
    )
