"""Product matching service — maps skin analysis to product recommendations."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import Product
from app.services.skin_analyzer import SkinAnalysis

# Skincare routine step order and what categories map to each step
STEP_CATEGORY_MAP = {
    "Cleanse": ["cleanser"],
    "Tone": ["toner"],
    "Treat": ["serum", "treatment"],
    "Moisturize": ["moisturizer", "mask"],
    "Protect": ["sunscreen"],
}

# Concern-to-ingredient reason mapping
CONCERN_REASONS = {
    "acne": "Targets breakouts and blemishes",
    "pores": "Minimizes pore appearance",
    "oiliness": "Controls excess sebum production",
    "dryness": "Provides deep hydration",
    "pigmentation": "Reduces dark spots and evens skin tone",
    "redness": "Soothes irritation and reduces redness",
    "wrinkles": "Anti-aging and skin firming",
}


def _calculate_match_score(product: Product, analysis: SkinAnalysis) -> float:
    """
    Calculate how well a product matches the analysis results.
    Higher score = better match.
    """
    score = 0.0

    # +30 points if product matches detected skin type
    skin_type_lower = analysis.skin_type.lower()
    product_skin_types = [st.lower() for st in (product.skin_types or [])]
    if skin_type_lower in product_skin_types or "all" in product_skin_types:
        score += 30.0

    # Weighted scoring based on concern severity
    product_concerns = [c.lower() for c in (product.concerns or [])]
    for concern, severity in analysis.concern_severities.items():
        if concern in product_concerns:
            # Map 0-100 severity to 0-30 points weight
            score += (severity * 0.3)

    return score


def _get_reason(product: Product, analysis: SkinAnalysis) -> str:
    """Generate a human-readable reason for recommending this product."""
    product_concerns = [c.lower() for c in (product.concerns or [])]
    matching = [c for c in analysis.concerns if c in product_concerns]

    if matching:
        # Pick the matching concern with the highest severity
        top_concern = max(matching, key=lambda c: analysis.concern_severities.get(c, 0))
        return CONCERN_REASONS.get(top_concern, f"Targets {top_concern}")

    skin_type_lower = analysis.skin_type.lower()
    product_skin_types = [st.lower() for st in (product.skin_types or [])]
    if skin_type_lower in product_skin_types:
        return f"Formulated for {analysis.skin_type} skin"

    return "General skincare recommendation"


async def match_products(
    db: AsyncSession,
    tenant_id: str,
    analysis: SkinAnalysis,
) -> list[dict]:
    """
    Match skin analysis results to products from the tenant's catalog.

    Strategy:
    1. Fetch all active products for this tenant
    2. Score each product based on skin type + concern matching
    3. Group by skincare routine step (Cleanse → Tone → Treat → Moisturize → Protect)
    4. Pick the top product per step

    Returns list of recommendation dicts ready for the API response.
    """
    # Fetch tenant's active products
    result = await db.execute(
        select(Product).where(
            Product.tenant_id == tenant_id,
            Product.is_active == True,
        )
    )
    products = result.scalars().all()

    if not products:
        return []

    # Score each product
    scored_products = []
    for product in products:
        score = _calculate_match_score(product, analysis)
        scored_products.append((product, score))

    # Sort by score descending
    scored_products.sort(key=lambda x: x[1], reverse=True)

    # Group into routine steps and sort
    step_products = {step: [] for step in STEP_CATEGORY_MAP.keys()}

    for product, score in scored_products:
        if score <= 0:
            continue

        category = product.category.lower()
        for step, categories in STEP_CATEGORY_MAP.items():
            if category in categories:
                step_products[step].append(product)
                break

    recommendations = []
    for step in list(STEP_CATEGORY_MAP.keys()):
        products_for_step = step_products.get(step, [])
        if not products_for_step:
            continue

        # Top product
        top_product = products_for_step[0]
        
        # Up to 2 alternatives
        alts = []
        for alt_prod in products_for_step[1:3]:
            alts.append({
                "product_id": alt_prod.id,
                "product_name": alt_prod.name,
                "reason": _get_reason(alt_prod, analysis)
            })

        recommendations.append({
            "step": step,
            "product_id": top_product.id,
            "product_name": top_product.name,
            "reason": _get_reason(top_product, analysis),
            "alternatives": alts
        })

    return recommendations
