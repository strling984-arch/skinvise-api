# 🧴 SkinVise AI Engine

**B2B SaaS API** for skincare e-commerce platforms. Analyze skin from face photos and get personalized product recommendations.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the server
uvicorn app.main:app --reload --port 8000

# 3. Open API docs
# http://localhost:8000/docs
```

## API Endpoints

### 🔐 Tenant Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/tenants` | Register a new store (returns API key) |
| `GET` | `/v1/tenants/me` | Get your store info + stats |
| `GET` | `/v1/tenants/me/history` | View past analyses |
| `POST` | `/v1/tenants/me/regenerate-key` | Get a new API key |

### 📦 Product Catalog
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/products` | Add a single product |
| `POST` | `/v1/products/import` | Bulk import from CSV/Excel |
| `GET` | `/v1/products` | List your products |
| `DELETE` | `/v1/products/{id}` | Remove a product |

### 🔬 Skin Analysis
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/analyze-skin` | Analyze a face photo → get recommendations |

## Authentication

All endpoints (except tenant registration) require an `X-API-Key` header:

```bash
curl -H "X-API-Key: sv_your_key_here" http://localhost:8000/v1/tenants/me
```

## Usage Example

```bash
# 1. Register your store
curl -X POST http://localhost:8000/v1/tenants \
  -H "Content-Type: application/json" \
  -d '{"name": "My Skin Shop", "email": "shop@example.com"}'

# 2. Import your product catalog
curl -X POST http://localhost:8000/v1/products/import \
  -H "X-API-Key: sv_YOUR_KEY" \
  -F "file=@sample_data/products_sample.csv"

# 3. Analyze skin
curl -X POST http://localhost:8000/v1/analyze-skin \
  -H "X-API-Key: sv_YOUR_KEY" \
  -F "image=@face_photo.jpg"
```

## Response Example

```json
{
  "analysis": {
    "skin_type": "Combination",
    "score": { "hydration": 45, "oiliness": 72, "clarity": 60 },
    "concerns": ["oiliness", "pores", "pigmentation"]
  },
  "recommendations": [
    { "step": "Cleanse", "product_id": "...", "product_name": "ClearPore Foam Cleanser", "reason": "Controls excess sebum production" },
    { "step": "Treat", "product_id": "...", "product_name": "Niacinamide 10% Serum", "reason": "Minimizes pore appearance" },
    { "step": "Moisturize", "product_id": "...", "product_name": "Oil-Free Gel Moisturizer", "reason": "Controls excess sebum production" },
    { "step": "Protect", "product_id": "...", "product_name": "Mattifying Sunscreen SPF30", "reason": "Controls excess sebum production" }
  ],
  "flagged_medical": false,
  "medical_note": null
}
```

## Tech Stack

- **Python 3.10+** / **FastAPI**
- **SQLAlchemy** (async) + **SQLite** (dev) / **PostgreSQL** (prod)
- **OpenCV** — Image validation & skin analysis
- **Pandas** — CSV/Excel product import
- **bcrypt** — API key hashing
