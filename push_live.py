import requests
import time
import sys

BASE_URL = "https://skinvise-api.onrender.com"

def main():
    print("Creating tenant on live server...")
    email = f"livedemo_{int(time.time())}@skin1004.com"
    res = requests.post(f"{BASE_URL}/v1/tenants", json={
        "name": "SKIN1004 Centella Live",
        "email": email,
        "domain": "skin1004.com"
    })
    
    if res.status_code != 201:
        print(f"Error creating tenant: {res.text}")
        sys.exit(1)
        
    data = res.json()
    api_key = data.get("api_key")
    if not api_key:
        print("API Key not returned!")
        sys.exit(1)
        
    print(f"Created Tenant successfully. API Key: {api_key}")
    
    print("Uploading products...")
    with open("sample_data/centella_products.csv", "rb") as f:
        files = {"file": ("centella_products.csv", f, "text/csv")}
        headers = {"X-API-Key": api_key}
        import_res = requests.post(
            f"{BASE_URL}/v1/products/import",
            headers=headers,
            files=files
        )
        
    if import_res.status_code != 200:
        print(f"Error importing products: {import_res.text}")
        sys.exit(1)
        
    print("Import successful:")
    print(import_res.json())
    print("\n--- SUCCESS ---")
    print(api_key)

if __name__ == "__main__":
    main()
