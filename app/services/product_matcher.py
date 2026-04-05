"""Product matching service — maps skin/hair analysis to product recommendations."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import Product

# Skincare routine step order and what categories map to each step
SKIN_STEP_CATEGORY_MAP = {
    "Cleanse": ["cleanser"],
    "Tone": ["toner"],
    "Treat": ["serum", "treatment"],
    "Moisturize": ["moisturizer", "mask"],
    "Protect": ["sunscreen"],
}

HAIR_STEP_CATEGORY_MAP = {
    "Cleanse": ["shampoo"],
    "Condition": ["conditioner"],
    "Treat": ["hair_mask", "scalp_treatment"],
    "Style": ["hair_oil", "styling"],
}

BODY_STEP_CATEGORY_MAP = {
    "Cleanse": ["body_wash"],
    "Exfoliate": ["body_scrub"],
    "Moisturize": ["body_lotion", "body_oil"],
    "Protect": ["deodorant", "sunscreen"],
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
    "frizz": "Smooths cuticle to reduce frizz",
    "dullness": "Enhances shine and natural glow",
    "flatness": "Boosts volume and body",
    "damage": "Repairs and strengthens keratin structure",
    "keratosis": "Gently exfoliates rough bumps",
}

def _calculate_match_score(product: Product, analysis) -> float:
    score = 0.0

    target_type = getattr(analysis, "skin_type", getattr(analysis, "hair_type", "all")).lower()
    product_types = [st.lower() for st in (product.skin_types or [])]
    if target_type in product_types or "all" in product_types:
        score += 30.0

    product_concerns = [c.lower() for c in (product.concerns or [])]
    for concern, severity in analysis.concern_severities.items():
        if concern in product_concerns:
            score += (severity * 0.3)

    return score


def _get_reason(product: Product, analysis) -> str:
    product_concerns = [c.lower() for c in (product.concerns or [])]
    matching = [c for c in analysis.concerns if c in product_concerns]

    if matching:
        top_concern = max(matching, key=lambda c: analysis.concern_severities.get(c, 0))
        return CONCERN_REASONS.get(top_concern, f"Targets {top_concern}")

    target_type = getattr(analysis, "skin_type", getattr(analysis, "hair_type", "all")).lower()
    product_types = [st.lower() for st in (product.skin_types or [])]
    if target_type in product_types:
        return f"Formulated for {target_type} type"

    return "General recommendation"


async def match_products(
    db: AsyncSession,
    tenant_id: str,
    analysis,
    routine_type: str = "skin"
) -> list[dict]:
    
    result = await db.execute(
        select(Product).where(
            Product.tenant_id == tenant_id,
            Product.is_active == True,
        )
    )
    products = result.scalars().all()

    if not products:
        return []

    scored_products = []
    for product in products:
        score = _calculate_match_score(product, analysis)
        scored_products.append((product, score))

    scored_products.sort(key=lambda x: x[1], reverse=True)

    if routine_type == "hair":
        step_map = HAIR_STEP_CATEGORY_MAP
    elif routine_type == "body":
        step_map = BODY_STEP_CATEGORY_MAP
    else:
        step_map = SKIN_STEP_CATEGORY_MAP

    step_products = {step: [] for step in step_map.keys()}

    for product, score in scored_products:
        if score <= 0:
            continue

        category = product.category.lower()
        for step, categories in step_map.items():
            if category in categories:
                step_products[step].append(product)
                break

    recommendations = []
    for step in list(step_map.keys()):
        products_for_step = step_products.get(step, [])
        if not products_for_step:
            continue

        top_product = products_for_step[0]
        
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
