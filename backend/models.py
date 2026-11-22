from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Date, DateTime, ForeignKey, Text
)
from sqlalchemy.orm import relationship
from backend.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), default="Bakery Owner")
    created_at = Column(DateTime, default=datetime.utcnow)


class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    category = Column(String(50), default="General")  # Flour, Dairy, Sugar, Flavors, Packaging, etc.
    quantity = Column(Float, default=0.0, nullable=False)  # Current stock
    unit = Column(String(20), default="g", nullable=False)  # g, kg, ml, L, pcs, etc.
    min_stock = Column(Float, default=0.0, nullable=False)  # Rule-based threshold
    cost_per_unit = Column(Float, default=0.0)  # Optional reference price
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    logs = relationship("InventoryLog", back_populates="ingredient", cascade="all, delete-orphan")
    recipe_ingredients = relationship("RecipeIngredient", back_populates="ingredient")
    shopping_items = relationship("ShoppingItem", back_populates="ingredient")


class InventoryLog(Base):
    __tablename__ = "inventory_logs"

    id = Column(Integer, primary_key=True, index=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id", ondelete="SET NULL"), nullable=True)
    ingredient_name = Column(String(100), nullable=False)  # Preserved even if ingredient deleted
    change_type = Column(String(50), nullable=False)  # BAKE_USAGE, RESTOCK_PURCHASE, SHOPPING_RESTOCK, MANUAL_ADJUSTMENT, WASTE
    quantity_delta = Column(Float, nullable=False)  # e.g. -250.0 or +1000.0
    quantity_before = Column(Float, nullable=False)
    quantity_after = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    reason = Column(String(255), nullable=True)  # e.g., "Baked 2x Pineapple Cake", "Bought from Supermarket"
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    ingredient = relationship("Ingredient", back_populates="logs")


class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False, unique=True, index=True)
    category = Column(String(50), default="Cakes")  # Cakes, Cupcakes, Frosting, Cookies
    yield_quantity = Column(Float, default=1.0)
    yield_unit = Column(String(50), default="cake (1 kg)")
    instructions = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Ingredients required
    ingredients = relationship("RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan")
    bakes = relationship("BakeEvent", back_populates="recipe")


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Float, nullable=False)  # Amount per recipe yield
    unit = Column(String(20), nullable=False)  # g, ml, pcs, etc.

    recipe = relationship("Recipe", back_populates="ingredients")
    ingredient = relationship("Ingredient", back_populates="recipe_ingredients")


class BakeEvent(Base):
    __tablename__ = "bake_events"

    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="SET NULL"), nullable=True)
    recipe_name = Column(String(120), nullable=False)
    multiplier = Column(Float, default=1.0)  # e.g. 2 for 2 batches
    date = Column(Date, default=date.today, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    recipe = relationship("Recipe", back_populates="bakes")


class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    cake_type = Column(String(120), nullable=False, index=True)
    quantity = Column(Float, default=1.0, nullable=False)
    amount = Column(Float, nullable=False)  # Total sales revenue in Rs
    date = Column(Date, default=date.today, index=True, nullable=False)
    customer_name = Column(String(100), nullable=True)
    payment_method = Column(String(50), default="Cash")  # Cash, UPI, Card, Other
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True, index=True)
    bill_total = Column(Float, nullable=False)  # Total expense in Rs
    date = Column(Date, default=date.today, index=True, nullable=False)
    supplier = Column(String(100), nullable=True)  # Store/Supplier name
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Optional itemized line items
    items = relationship("PurchaseItem", back_populates="purchase", cascade="all, delete-orphan")


class PurchaseItem(Base):
    __tablename__ = "purchase_items"

    id = Column(Integer, primary_key=True, index=True)
    purchase_id = Column(Integer, ForeignKey("purchases.id", ondelete="CASCADE"), nullable=False)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id", ondelete="SET NULL"), nullable=True)
    item_name = Column(String(100), nullable=False)
    quantity = Column(Float, default=1.0)
    unit = Column(String(20), default="pcs")
    cost = Column(Float, default=0.0)

    purchase = relationship("Purchase", back_populates="items")


class ShoppingItem(Base):
    __tablename__ = "shopping_items"

    id = Column(Integer, primary_key=True, index=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(100), nullable=False)
    quantity = Column(Float, default=1.0)
    unit = Column(String(20), default="pcs")
    is_bought = Column(Boolean, default=False, index=True)
    is_from_warning = Column(Boolean, default=False)
    notes = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    bought_at = Column(DateTime, nullable=True)

    ingredient = relationship("Ingredient", back_populates="shopping_items")
