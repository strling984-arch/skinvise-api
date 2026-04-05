import requests
import csv
import io

BASE_URL = "https://skinvise-api.onrender.com"
CSV_PATH = "sample_data/products_sample.csv"

def setup():
    print(f"--- Initializing SkinVise Production at {BASE_URL} ---")
    
    # 1. Create Tenant
    import time
    timestamp = int(time.time())
    try:
        tenant_res = requests.post(f"{BASE_URL}/v1/tenants", json={
            "name": f"SkinVise Demo Store {timestamp}",
            "email": f"demo_{timestamp}@skinvise.ai",
            "domain": "https://skinvise-api.vercel.app"
        })
        tenant_res.raise_for_status()
        api_key = tenant_res.json()["api_key"]
        print(f"✅ Created Tenant. API Key: {api_key}")
    except Exception as e:
        print(f"❌ Error creating tenant: {e}")
        return

    # 2. Import Products
    try:
        with open(CSV_PATH, 'rb') as f:
            files = {'file': ('products.csv', f, 'text/csv')}
            import_res = requests.post(
                f"{BASE_URL}/v1/products/import", 
                headers={"X-API-Key": api_key},
                files=files
            )
            import_res.raise_for_status()
            res_data = import_res.json()
            print(f"✅ Import Result: {res_data}")
            if res_data.get("errors"):
                print(f"⚠️ Import Errors: {res_data['errors']}")
            print(f"✅ Imported {res_data.get('imported', 0)} products into production.")
    except Exception as e:
        print(f"❌ Error importing products: {e}")
        if 'import_res' in locals():
            print(f"Response: {import_res.text}")
        return

    print("\n--- SETUP COMPLETE ---")
    print(f"LIVE DEMO URL: https://skinvise-api.vercel.app")
    print(f"YOUR PRODUCTION API KEY: {api_key}")
    print("-----------------------")

if __name__ == "__main__":
    setup()
