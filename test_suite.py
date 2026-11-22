import os
import sys
from dotenv import load_dotenv
from fastapi.testclient import TestClient

load_dotenv()
from backend.main import app

def run_tests():
    client = TestClient(app)

    print("--- TEST 1: Login & Auth ---")
    owner_username = os.getenv("OWNER_USERNAME", "mom")
    owner_password = os.getenv("OWNER_PASSWORD")
    assert owner_password, "OWNER_PASSWORD environment variable must be set in .env"

    # Bad login
    bad_login = client.post("/api/auth/login", json={"username": owner_username, "password": "wrongpassword_12345"})
    assert bad_login.status_code == 401, f"Expected 401, got {bad_login.status_code}"

    # Good login
    good_login = client.post("/api/auth/login", json={"username": owner_username, "password": owner_password})
    assert good_login.status_code == 200, f"Expected 200, got {good_login.status_code}"
    token = good_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[PASS] Login successful with JWT token!")

    print("--- TEST 2: Sales CRUD & Summaries ---")
    sale_payload = {
        "cake_type": "Custom Butterscotch Cake (1 kg)",
        "quantity": 1.0,
        "amount": 800.0,
        "date": "2026-11-21",
        "customer_name": "Meera Verma",
        "payment_method": "UPI",
        "notes": "Test sale in person"
    }
    s_res = client.post("/api/sales", json=sale_payload, headers=headers)
    assert s_res.status_code == 201, f"Expected 201, got {s_res.status_code}: {s_res.text}"
    sale_id = s_res.json()["id"]
    print(f"[PASS] Sale recorded with ID: {sale_id}")

    summary_res = client.get("/api/sales/summary", headers=headers)
    assert summary_res.status_code == 200
    s_data = summary_res.json()
    assert s_data["today_total"] >= 800.0
    print(f"[PASS] Sales Summary - Today: Rs.{s_data['today_total']}, Month: Rs.{s_data['this_month_total']}")

    print("--- TEST 3: Purchases CRUD & Stock Credit ---")
    ings = client.get("/api/inventory?search=Butter", headers=headers).json()
    assert len(ings) > 0
    butter = ings[0]
    butter_id = butter["id"]
    butter_qty_before = butter["quantity"]
    print(f"Butter quantity before purchase: {butter_qty_before} {butter['unit']}")

    purchase_payload = {
        "bill_total": 550.0,
        "date": "2026-11-21",
        "supplier": "Metro Cash & Carry",
        "notes": "Restocked butter slab",
        "update_inventory_stock": True,
        "items": [{
            "ingredient_id": butter_id,
            "item_name": butter["name"],
            "quantity": 1000.0,
            "unit": "g",
            "cost": 550.0
        }]
    }
    p_res = client.post("/api/purchases", json=purchase_payload, headers=headers)
    assert p_res.status_code == 201, f"Expected 201, got {p_res.status_code}: {p_res.text}"

    # Verify stock updated
    butter_after = client.get(f"/api/inventory/{butter_id}", headers=headers).json()
    expected_qty = butter_qty_before + 1000.0
    assert butter_after["quantity"] == expected_qty, f"Expected {expected_qty}, got {butter_after['quantity']}"
    print(f"[PASS] Butter quantity after purchase: {butter_after['quantity']} {butter_after['unit']}")

    print("--- TEST 4: Recipe Bake Confirmation Workflow ---")
    recipes = client.get("/api/recipes", headers=headers).json()
    rec = recipes[0]
    rec_id = rec["id"]
    print(f"Testing bake on recipe: {rec['name']}")

    preview = client.get(f"/api/recipes/{rec_id}/bake-preview?multiplier=1.0", headers=headers).json()
    assert "items" in preview and "can_bake" in preview
    print(f"[PASS] Bake preview - can bake: {preview['can_bake']}, items checked: {len(preview['items'])}")

    # Confirm bake
    confirm_res = client.post(
        f"/api/recipes/{rec_id}/bake-confirm",
        json={"recipe_id": rec_id, "multiplier": 1.0},
        headers=headers
    )
    assert confirm_res.status_code == 200, f"Confirm bake failed: {confirm_res.text}"
    c_data = confirm_res.json()
    assert c_data["success"] is True
    print(f"[PASS] Bake confirmed! Deductions made for {len(c_data['deductions'])} ingredients.")

    # Verify InventoryLog has BAKE_USAGE
    logs = client.get("/api/inventory/logs?change_type=BAKE_USAGE", headers=headers).json()
    assert len(logs) > 0
    print(f"[PASS] Latest bake usage log: {logs[0]['reason']}, Delta: {logs[0]['quantity_delta']} {logs[0]['unit']}")

    print("--- TEST 5: Shopping List & Mark Bought ---")
    # Auto add low stock
    auto_res = client.post("/api/shopping/auto-add-low-stock", headers=headers)
    assert auto_res.status_code == 200
    print(f"[PASS] Auto add low stock: {auto_res.json()['message']}")

    # Add manual item
    add_shop = client.post("/api/shopping", json={"name": "Almond Flakes", "quantity": 250.0, "unit": "g"}, headers=headers)
    assert add_shop.status_code == 201
    shop_item = add_shop.json()
    shop_id = shop_item["id"]

    # Mark bought
    mark_res = client.post(
        f"/api/shopping/{shop_id}/mark-bought",
        json={"update_inventory": True, "actual_quantity": 250.0},
        headers=headers
    )
    assert mark_res.status_code == 200
    print(f"[PASS] Mark bought completed: {mark_res.json()['message']}")

    print("--- TEST 6: Dashboard Metrics ---")
    dash = client.get("/api/dashboard/metrics", headers=headers).json()
    print(f"[PASS] Sales month: Rs.{dash['sales_month']}")
    print(f"[PASS] Purchases month: Rs.{dash['purchases_month']}")
    print(f"[PASS] Sales minus purchases month: Rs.{dash['sales_minus_purchases_month']} (Explicitly NOT labeled profit)")
    print(f"[PASS] Shortage predictor status: {dash['shortage_predictor']['status_label']}")
    print(f"[PASS] Shortage predictor explanation: {dash['shortage_predictor']['explanation']}")
    assert dash["shortage_predictor"]["status_label"] == "Not enough data yet"

    print("--- TEST 7: CSV Exports ---")
    for exp in ["sales", "purchases", "inventory", "inventory-logs"]:
        csv_res = client.get(f"/api/exports/{exp}.csv", headers=headers)
        assert csv_res.status_code == 200
        assert "text/csv" in csv_res.headers["content-type"]
        line_count = len(csv_res.text.strip().splitlines())
        assert line_count > 1
        print(f"[PASS] CSV export '{exp}.csv' OK ({line_count} rows)")

    print("\n==============================================")
    print("  ALL 7 CORE REQUIREMENTS TESTED & PASSED OK  ")
    print("==============================================")

if __name__ == "__main__":
    run_tests()
