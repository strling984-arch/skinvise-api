"""Product catalog management endpoints."""

import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd

from app.database import get_db
from app.middleware.auth import get_current_tenant
from app.models.db_models import Tenant, Product
from app.schemas.schemas import ProductCreate, ProductResponse, ProductImportResult, MessageResponse

router = APIRouter(prefix="/v1/products", tags=["Products"])

VALID_CATEGORIES = {
    # Skin
    "cleanser", "moisturizer", "serum", "sunscreen", "treatment", "toner", "mask",
    # Hair
    "shampoo", "conditioner", "hair_mask", "hair_oil", "scalp_treatment", "styling",
    # Body
    "body_wash", "body_scrub", "body_lotion", "body_oil", "deodorant"
}
VALID_SKIN_TYPES = {"oily", "dry", "combination", "normal", "sensitive", "all"}
VALID_CONCERNS = {
    "acne", "pores", "oiliness", "dryness", "pigmentation", "redness", "wrinkles",
    "frizz", "dullness", "flatness", "damage", "keratosis"
}


def _validate_product_data(data: ProductCreate) -> list[str]:
    """Validate product fields, return list of errors."""
    errors = []
    if data.category.lower() not in VALID_CATEGORIES:
        errors.append(f"Invalid category '{data.category}'. Valid: {', '.join(VALID_CATEGORIES)}")
    for st in data.skin_types:
        if st.lower() not in VALID_SKIN_TYPES:
            errors.append(f"Invalid skin type '{st}'. Valid: {', '.join(VALID_SKIN_TYPES)}")
    for c in data.concerns:
        if c.lower() not in VALID_CONCERNS:
            errors.append(f"Invalid concern '{c}'. Valid: {', '.join(VALID_CONCERNS)}")
    return errors


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a product to your catalog",
)
async def create_product(
    product_data: ProductCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    # Validate
    errors = _validate_product_data(product_data)
    if errors:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="; ".join(errors))

    # Check duplicate SKU
    existing = await db.execute(
        select(Product).where(
            Product.tenant_id == tenant.id,
            Product.sku == product_data.sku,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Product with SKU '{product_data.sku}' already exists.",
        )

    product = Product(
        tenant_id=tenant.id,
        sku=product_data.sku,
        name=product_data.name,
        category=product_data.category.lower(),
        skin_types=[st.lower() for st in product_data.skin_types],
        concerns=[c.lower() for c in product_data.concerns],
        description=product_data.description,
        price=product_data.price,
        currency=product_data.currency,
        image_url=product_data.image_url,
    )
    db.add(product)
    await db.flush()
    await db.refresh(product)
    return ProductResponse.model_validate(product)


@router.post(
    "/import",
    response_model=ProductImportResult,
    summary="Bulk import products from CSV/Excel",
    description=(
        "Upload a CSV or Excel file with columns: "
        "sku, name, category, skin_types (comma-sep), concerns (comma-sep), "
        "description, price, currency, image_url"
    ),
)
async def import_products(
    file: UploadFile = File(..., description="CSV or Excel file"),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> ProductImportResult:
    # Read file
    contents = await file.read()
    filename = file.filename or ""

    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(contents))
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(contents))
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be .csv or .xlsx",
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not parse file: {str(e)}",
        )

    # Required columns
    required_cols = {"sku", "name", "category"}
    if not required_cols.issubset(set(df.columns)):
        missing = required_cols - set(df.columns)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Missing required columns: {', '.join(missing)}",
        )

    # Get existing SKUs
    existing_result = await db.execute(
        select(Product.sku).where(Product.tenant_id == tenant.id)
    )
    existing_skus = {row[0] for row in existing_result.all()}

    imported = 0
    skipped = 0
    errors = []

    for idx, row in df.iterrows():
        try:
            sku = str(row["sku"]).strip()
            if sku in existing_skus:
                skipped += 1
                continue

            # Parse comma-separated fields
            skin_types = []
            if "skin_types" in row and pd.notna(row["skin_types"]):
                skin_types = [s.strip().lower() for s in str(row["skin_types"]).split(",")]

            concerns = []
            if "concerns" in row and pd.notna(row["concerns"]):
                concerns = [c.strip().lower() for c in str(row["concerns"]).split(",")]

            category = str(row["category"]).strip().lower()
            if category not in VALID_CATEGORIES:
                errors.append(f"Row {idx + 2}: Invalid category '{category}'")
                skipped += 1
                continue

            product = Product(
                tenant_id=tenant.id,
                sku=sku,
                name=str(row["name"]).strip(),
                category=category,
                skin_types=skin_types,
                concerns=concerns,
                description=str(row.get("description", "")).strip() if pd.notna(row.get("description")) else None,
                price=float(row["price"]) if "price" in row and pd.notna(row.get("price")) else None,
                currency=str(row.get("currency", "USD")).strip() if pd.notna(row.get("currency")) else "USD",
                image_url=str(row.get("image_url", "")).strip() if pd.notna(row.get("image_url")) else None,
            )
            db.add(product)
            existing_skus.add(sku)
            imported += 1

        except Exception as e:
            errors.append(f"Row {idx + 2}: {str(e)}")
            skipped += 1

    await db.flush()

    return ProductImportResult(
        total_rows=len(df),
        imported=imported,
        skipped=skipped,
        errors=errors[:20],  # Limit error messages
    )


@router.get(
    "",
    response_model=list[ProductResponse],
    summary="List all products in your catalog",
)
async def list_products(
    category: str | None = None,
    limit: int = 100,
    offset: int = 0,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> list[ProductResponse]:
    query = select(Product).where(
        Product.tenant_id == tenant.id,
        Product.is_active == True,
    )
    if category:
        query = query.where(Product.category == category.lower())

    query = query.order_by(Product.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    products = result.scalars().all()
    return [ProductResponse.model_validate(p) for p in products]


@router.delete(
    "/{product_id}",
    response_model=MessageResponse,
    summary="Delete a product from your catalog",
)
async def delete_product(
    product_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.tenant_id == tenant.id,
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )

    await db.delete(product)
    await db.flush()
    return MessageResponse(message=f"Product '{product.name}' deleted successfully.")
