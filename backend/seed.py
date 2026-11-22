import os
import sys
import secrets
from datetime import date, timedelta
from dotenv import load_dotenv

# Ensure root directory is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from sqlalchemy.orm import Session
from backend.database import SessionLocal, Base, engine
from backend.models import (
    User, Ingredient, InventoryLog, Recipe, RecipeIngredient,
    Sale, Purchase, PurchaseItem, ShoppingItem, BakeEvent
)
from backend.auth import hash_password, verify_password

# Load environment variables
ENV_FILE = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_FILE)

def get_or_create_owner_credentials():
    username = os.getenv("OWNER_USERNAME", "mom").strip().lower()
    password = os.getenv("OWNER_PASSWORD")

    if not password or not password.strip():
        # Generate a secure random 12-character alphanumeric password
        alphabet = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        password = "".join(secrets.choice(alphabet) for _ in range(12))

        # Append to .env file
        env_line = f"\nOWNER_PASSWORD={password}\n"
        with open(ENV_FILE, "a" if os.path.exists(ENV_FILE) else "w") as f:
            f.write(env_line)
        print(f"[Auth] No OWNER_PASSWORD set in environment. Generated random initial password and saved to .env.")

    return username, password.strip()

def seed_database():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    try:
        # 1. Owner User from Environment Variable
        owner_username, owner_password = get_or_create_owner_credentials()

        owner = db.query(User).filter(User.username == owner_username).first()
        if not owner:
            owner = User(
                username=owner_username,
                hashed_password=hash_password(owner_password),
                full_name="Baker Mom"
            )
            db.add(owner)
            db.flush()
            print(f"[Seed] Created initial owner user '{owner_username}' using environment password.")
        else:
            # Sync password if it does not match current environment password
            if not verify_password(owner_password, owner.hashed_password):
                owner.hashed_password = hash_password(owner_password)
                print(f"[Seed] Updated password for owner '{owner_username}' from environment configuration.")

        # 2. Ingredients
        if db.query(Ingredient).count() == 0:
            sample_ingredients = [
                ("All-Purpose Flour (Maida)", "Flour & Dry", 4500.0, "g", 2000.0, 0.05, "Standard unbleached flour"),
                ("Castor Sugar", "Sweeteners", 3200.0, "g", 1500.0, 0.06, "Fine baking sugar"),
                ("Unsalted Butter", "Dairy", 1200.0, "g", 1000.0, 0.55, "Amul or home dairy"),
                ("Cocoa Powder (Dutch Process)", "Cocoa & Flavors", 350.0, "g", 500.0, 0.90, "Rich alkalized cocoa"),
                ("Dark Chocolate Compound", "Cocoa & Flavors", 700.0, "g", 1000.0, 0.40, "55% dark baking slab"),
                ("Pure Vanilla Extract", "Cocoa & Flavors", 120.0, "ml", 100.0, 2.50, "Madagascar vanilla extract"),
                ("Whipping Cream (Non-Dairy)", "Dairy", 1500.0, "ml", 2000.0, 0.18, "Rich's or Tropolite topping"),
                ("Fresh Eggs", "Dairy", 24.0, "pcs", 12.0, 7.00, "Farm fresh brown/white eggs"),
                ("Baking Powder", "Leavening", 300.0, "g", 150.0, 0.30, "Double acting baking powder"),
                ("Baking Soda", "Leavening", 250.0, "g", 100.0, 0.20, "Pure sodium bicarbonate"),
                ("Pineapple Crushed / Compote", "Fruits & Fillings", 600.0, "g", 500.0, 0.25, "Tin / canned fruit crush"),
                ("Cake Boards (8-inch round)", "Packaging", 8.0, "pcs", 15.0, 15.00, "Gold/Silver sturdy board"),
                ("Cake Boxes (1 kg window)", "Packaging", 6.0, "pcs", 15.0, 22.00, "Sturdy corrugated box with handle")
            ]

            ing_map = {}
            for name, cat, qty, unit, min_s, cpu, notes in sample_ingredients:
                ing = Ingredient(
                    name=name,
                    category=cat,
                    quantity=qty,
                    unit=unit,
                    min_stock=min_s,
                    cost_per_unit=cpu,
                    notes=notes
                )
                db.add(ing)
                db.flush()
                ing_map[name] = ing

                # Log initial inventory
                log = InventoryLog(
                    ingredient_id=ing.id,
                    ingredient_name=ing.name,
                    change_type="MANUAL_ADJUSTMENT",
                    quantity_delta=qty,
                    quantity_before=0.0,
                    quantity_after=qty,
                    unit=unit,
                    reason="Initial stock baseline"
                )
                db.add(log)

            print(f"[Seed] Added {len(sample_ingredients)} ingredients with inventory history.")

            # 3. Recipes
            choco_recipe = Recipe(
                name="Classic Chocolate Truffle Cake (1 kg)",
                category="Cakes",
                yield_quantity=1.0,
                yield_unit="cake (1 kg)",
                instructions="Bake chocolate sponge at 170C for 35 mins. Layer with dark chocolate ganache and chocolate curls."
            )
            db.add(choco_recipe)
            db.flush()

            choco_items = [
                (ing_map["All-Purpose Flour (Maida)"], 250.0, "g"),
                (ing_map["Castor Sugar"], 200.0, "g"),
                (ing_map["Cocoa Powder (Dutch Process)"], 75.0, "g"),
                (ing_map["Dark Chocolate Compound"], 200.0, "g"),
                (ing_map["Unsalted Butter"], 120.0, "g"),
                (ing_map["Whipping Cream (Non-Dairy)"], 250.0, "ml"),
                (ing_map["Baking Powder"], 8.0, "g"),
                (ing_map["Pure Vanilla Extract"], 5.0, "ml"),
                (ing_map["Cake Boards (8-inch round)"], 1.0, "pcs"),
                (ing_map["Cake Boxes (1 kg window)"], 1.0, "pcs")
            ]
            for ing, amt, u in choco_items:
                db.add(RecipeIngredient(recipe_id=choco_recipe.id, ingredient_id=ing.id, amount=amt, unit=u))

            pine_recipe = Recipe(
                name="Fresh Pineapple Cake (1 kg)",
                category="Cakes",
                yield_quantity=1.0,
                yield_unit="cake (1 kg)",
                instructions="Vanilla sponge layered with whipped cream and juicy pineapple crushed filling."
            )
            db.add(pine_recipe)
            db.flush()

            pine_items = [
                (ing_map["All-Purpose Flour (Maida)"], 220.0, "g"),
                (ing_map["Castor Sugar"], 180.0, "g"),
                (ing_map["Unsalted Butter"], 100.0, "g"),
                (ing_map["Whipping Cream (Non-Dairy)"], 300.0, "ml"),
                (ing_map["Pineapple Crushed / Compote"], 200.0, "g"),
                (ing_map["Baking Powder"], 6.0, "g"),
                (ing_map["Pure Vanilla Extract"], 5.0, "ml"),
                (ing_map["Cake Boards (8-inch round)"], 1.0, "pcs"),
                (ing_map["Cake Boxes (1 kg window)"], 1.0, "pcs")
            ]
            for ing, amt, u in pine_items:
                db.add(RecipeIngredient(recipe_id=pine_recipe.id, ingredient_id=ing.id, amount=amt, unit=u))

            vanilla_recipe = Recipe(
                name="Vanilla Butter Tea Cake (500 g)",
                category="Tea Cakes",
                yield_quantity=1.0,
                yield_unit="loaf (500 g)",
                instructions="Cream butter and sugar until pale, fold in flour and vanilla. Bake at 160C."
            )
            db.add(vanilla_recipe)
            db.flush()

            vanilla_items = [
                (ing_map["All-Purpose Flour (Maida)"], 150.0, "g"),
                (ing_map["Castor Sugar"], 120.0, "g"),
                (ing_map["Unsalted Butter"], 100.0, "g"),
                (ing_map["Fresh Eggs"], 2.0, "pcs"),
                (ing_map["Baking Powder"], 4.0, "g"),
                (ing_map["Pure Vanilla Extract"], 5.0, "ml")
            ]
            for ing, amt, u in vanilla_items:
                db.add(RecipeIngredient(recipe_id=vanilla_recipe.id, ingredient_id=ing.id, amount=amt, unit=u))

            print("[Seed] Added 3 homemade cake recipes.")

        # 4. Shopping list auto items if none
        if db.query(ShoppingItem).count() == 0:
            lows = db.query(Ingredient).filter(Ingredient.quantity <= Ingredient.min_stock).all()
            for l in lows:
                needed = (l.min_stock * 2) - l.quantity
                db.add(ShoppingItem(
                    ingredient_id=l.id,
                    name=l.name,
                    quantity=round(needed, 2),
                    unit=l.unit,
                    notes=f"Low stock alert: {round(l.quantity, 2)} {l.unit} left",
                    is_bought=False,
                    is_from_warning=True
                ))

        # 5. Realistic initial Sales & Purchases
        if db.query(Sale).count() == 0:
            today = date.today()
            sample_sales = [
                (today, "Classic Chocolate Truffle Cake (1 kg)", 1.0, 750.0, "Mrs. Sharma", "UPI", "Birthday cake - pickup at 4 PM"),
                (today, "Vanilla Butter Tea Cake (500 g)", 2.0, 500.0, "Ankit Neighbor", "Cash", "Evening snacks order"),
                (today - timedelta(days=1), "Fresh Pineapple Cake (1 kg)", 1.0, 650.0, "Deepa", "UPI", "Anniversary celebration"),
                (today - timedelta(days=2), "Classic Chocolate Truffle Cake (1 kg)", 2.0, 1500.0, "Rajesh Family", "Cash", "Twins birthday"),
                (today - timedelta(days=4), "Fresh Pineapple Cake (1 kg)", 1.0, 650.0, "Kiran", "UPI", "In-person cash and carry")
            ]
            for s_date, c_type, qty, amt, cust, p_method, note in sample_sales:
                db.add(Sale(
                    cake_type=c_type,
                    quantity=qty,
                    amount=amt,
                    date=s_date,
                    customer_name=cust,
                    payment_method=p_method,
                    notes=note
                ))

            sample_purchases = [
                (today, 620.0, "Supermarket Wholesale", "Amul Butter 1kg, Milk pack"),
                (today - timedelta(days=2), 850.0, "Bake Mart Ingredients", "Cocoa powder 1kg, 20 cake boards & boxes"),
                (today - timedelta(days=5), 450.0, "Local Grocery Store", "Maida 5kg, Castor sugar 3kg")
            ]
            for p_date, tot, supp, note in sample_purchases:
                db.add(Purchase(
                    bill_total=tot,
                    date=p_date,
                    supplier=supp,
                    notes=note
                ))

            db.add(BakeEvent(
                recipe_name="Classic Chocolate Truffle Cake (1 kg)",
                multiplier=1.0,
                date=today,
                notes="Morning bake for Mrs. Sharma"
            ))

            print("[Seed] Added initial realistic sales, purchases, and bake events.")

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Seed] Error seeding database: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
