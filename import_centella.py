import asyncio
import pandas as pd
from app.database import engine, Base
from app.models.db_models import Tenant, Product
from app.middleware.auth import hash_api_key
import uuid

async def import_data():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.ext.asyncio import AsyncSession
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    async with async_session() as session:
        # Create a test tenant for Skin1004
        tenant_id = str(uuid.uuid4())
        # API KEY is "sv_centella_demo"
        api_key_hash = hash_api_key("sv_centella_demo")
        tenant = Tenant(
            id=tenant_id,
            name="SKIN1004 Official",
            email="demo@skin1004.com",
            domain="skin1004.com",
            api_key_hash=api_key_hash
        )
        session.add(tenant)
        await session.flush()
        
        # Read CSV and insert products
        df = pd.read_csv("sample_data/centella_products.csv")
        for _, row in df.iterrows():
            product = Product(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                sku=str(row["sku"]).strip(),
                name=str(row["name"]).strip(),
                category=str(row["category"]).strip().lower(),
                skin_types=[s.strip().lower() for s in str(row["skin_types"]).split(",")],
                concerns=[c.strip().lower() for c in str(row["concerns"]).split(",")],
                description=str(row.get("description", "")).strip(),
                price=float(row["price"]) if "price" in row else None,
                currency=str(row.get("currency", "USD")).strip(),
                image_url=str(row.get("image_url", "")).strip(),
            )
            session.add(product)
            
        await session.commit()
        print(f"Imported successfully! Tenant API Key: sv_centella_demo")

if __name__ == "__main__":
    asyncio.run(import_data())
