"""SQLAlchemy ORM models for multi-tenant SkinVise database."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    Index,
)
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import relationship
from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Tenant(Base):
    """A store/client using the SkinVise API."""

    __tablename__ = "tenants"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    domain = Column(String(255), nullable=True)
    api_key_hash = Column(String(255), nullable=False, unique=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    products = relationship("Product", back_populates="tenant", cascade="all, delete-orphan")
    analyses = relationship("AnalysisHistory", back_populates="tenant", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Tenant(id={self.id}, name={self.name})>"


class Product(Base):
    """A skincare product in a tenant's catalog."""

    __tablename__ = "products"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    sku = Column(String(100), nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False)  # cleanser, moisturizer, serum, sunscreen, treatment, toner, mask
    skin_types = Column(JSON, nullable=False, default=list)  # ["oily", "combination"]
    concerns = Column(JSON, nullable=False, default=list)  # ["acne", "pores", "oiliness"]
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=True)
    currency = Column(String(10), default="USD")
    image_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="products")

    # Indexes
    __table_args__ = (
        Index("ix_products_tenant_category", "tenant_id", "category"),
        Index("ix_products_tenant_sku", "tenant_id", "sku", unique=True),
    )

    def __repr__(self):
        return f"<Product(id={self.id}, name={self.name}, category={self.category})>"


class AnalysisHistory(Base):
    """Log of each skin analysis performed."""

    __tablename__ = "analysis_history"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    skin_type = Column(String(50), nullable=False)
    scores = Column(JSON, nullable=False)  # {"hydration": 45, "oiliness": 80, "clarity": 60}
    concerns = Column(JSON, nullable=False, default=list)  # ["acne", "pores"]
    recommendations = Column(JSON, nullable=False, default=list)  # [{"step": "Cleanse", "id": "...", "reason": "..."}]
    flagged_medical = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="analyses")

    # Indexes
    __table_args__ = (
        Index("ix_analysis_tenant_created", "tenant_id", "created_at"),
    )

    def __repr__(self):
        return f"<AnalysisHistory(id={self.id}, skin_type={self.skin_type})>"
