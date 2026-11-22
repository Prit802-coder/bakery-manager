from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

# ----------------- Auth Schemas -----------------
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=4)

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=4)

class UserOut(BaseModel):
    id: int
    username: str
    full_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ----------------- Ingredient Schemas -----------------
class IngredientBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    category: str = Field(default="General", max_length=50)
    quantity: float = Field(default=0.0, ge=0)
    unit: str = Field(default="g", max_length=20)
    min_stock: float = Field(default=0.0, ge=0)
    cost_per_unit: Optional[float] = Field(default=0.0, ge=0)
    notes: Optional[str] = None

class IngredientCreate(IngredientBase):
    pass

class IngredientUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[float] = Field(default=None, ge=0)
    unit: Optional[str] = None
    min_stock: Optional[float] = Field(default=None, ge=0)
    cost_per_unit: Optional[float] = None
    notes: Optional[str] = None

class IngredientStockAdjust(BaseModel):
    change_type: str = Field(..., pattern="^(RESTOCK_PURCHASE|MANUAL_ADJUSTMENT|WASTE|SHOPPING_RESTOCK)$")
    quantity_delta: float  # Can be positive (restock) or negative (waste/correction)
    reason: Optional[str] = None

class IngredientOut(IngredientBase):
    id: int
    is_low_stock: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ----------------- Inventory Log Schemas -----------------
class InventoryLogOut(BaseModel):
    id: int
    ingredient_id: Optional[int]
    ingredient_name: str
    change_type: str
    quantity_delta: float
    quantity_before: float
    quantity_after: float
    unit: str
    reason: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ----------------- Recipe Schemas -----------------
class RecipeIngredientItem(BaseModel):
    ingredient_id: int
    amount: float = Field(..., gt=0)
    unit: str = "g"

class RecipeIngredientDetail(BaseModel):
    id: int
    ingredient_id: int
    ingredient_name: str
    amount: float
    unit: str
    current_stock: float
    stock_unit: str

class RecipeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    category: str = Field(default="Cakes", max_length=50)
    yield_quantity: float = Field(default=1.0, gt=0)
    yield_unit: str = Field(default="cake (1 kg)", max_length=50)
    instructions: Optional[str] = None

class RecipeCreate(RecipeBase):
    ingredients: List[RecipeIngredientItem]

class RecipeUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    yield_quantity: Optional[float] = None
    yield_unit: Optional[str] = None
    instructions: Optional[str] = None
    ingredients: Optional[List[RecipeIngredientItem]] = None

class RecipeOut(RecipeBase):
    id: int
    ingredients: List[RecipeIngredientDetail]
    created_at: datetime

    class Config:
        from_attributes = True

# Baking confirmation workflow schemas
class BakePreviewRequest(BaseModel):
    recipe_id: int
    multiplier: float = Field(default=1.0, gt=0)

class BakeIngredientRequirement(BaseModel):
    ingredient_id: int
    ingredient_name: str
    required_amount: float
    unit: str
    current_stock: float
    stock_unit: str
    is_sufficient: bool
    stock_after_bake: float

class BakePreviewResponse(BaseModel):
    recipe_id: int
    recipe_name: str
    multiplier: float
    yield_description: str
    can_bake: bool
    items: List[BakeIngredientRequirement]
    warnings: List[str]

class BakeConfirmRequest(BaseModel):
    recipe_id: int
    multiplier: float = Field(default=1.0, gt=0)
    bake_date: Optional[date] = None
    notes: Optional[str] = None


# ----------------- Sales Schemas -----------------
class SaleCreate(BaseModel):
    cake_type: str = Field(..., min_length=1, max_length=120)
    quantity: float = Field(default=1.0, gt=0)
    amount: float = Field(..., ge=0)
    date: date
    customer_name: Optional[str] = None
    payment_method: Optional[str] = "Cash"
    notes: Optional[str] = None

class SaleUpdate(BaseModel):
    cake_type: Optional[str] = None
    quantity: Optional[float] = None
    amount: Optional[float] = None
    date: Optional[date] = None
    customer_name: Optional[str] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None

class SaleOut(BaseModel):
    id: int
    cake_type: str
    quantity: float
    amount: float
    date: date
    customer_name: Optional[str]
    payment_method: Optional[str]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class DailySummary(BaseModel):
    date: str
    total_amount: float
    count: int

class MonthlySummary(BaseModel):
    month: str  # YYYY-MM
    total_amount: float
    count: int

class SalesSummary(BaseModel):
    today_total: float
    today_count: int
    this_month_total: float
    this_month_count: int
    all_time_total: float
    all_time_count: int
    daily_breakdown: List[DailySummary]
    monthly_breakdown: List[MonthlySummary]


# ----------------- Purchases Schemas -----------------
class PurchaseItemCreate(BaseModel):
    ingredient_id: Optional[int] = None
    item_name: str
    quantity: float = 1.0
    unit: str = "pcs"
    cost: float = 0.0

class PurchaseItemOut(BaseModel):
    id: int
    ingredient_id: Optional[int]
    item_name: str
    quantity: float
    unit: str
    cost: float

    class Config:
        from_attributes = True

class PurchaseCreate(BaseModel):
    bill_total: float = Field(..., ge=0)
    date: date
    supplier: Optional[str] = None
    notes: Optional[str] = None
    items: Optional[List[PurchaseItemCreate]] = None
    update_inventory_stock: bool = False  # Checkbox to automatically credit stock

class PurchaseUpdate(BaseModel):
    bill_total: Optional[float] = None
    date: Optional[date] = None
    supplier: Optional[str] = None
    notes: Optional[str] = None

class PurchaseOut(BaseModel):
    id: int
    bill_total: float
    date: date
    supplier: Optional[str]
    notes: Optional[str]
    items: List[PurchaseItemOut]
    created_at: datetime

    class Config:
        from_attributes = True

class PurchasesSummary(BaseModel):
    today_total: float
    today_count: int
    this_month_total: float
    this_month_count: int
    all_time_total: float
    all_time_count: int
    daily_breakdown: List[DailySummary]
    monthly_breakdown: List[MonthlySummary]


# ----------------- Shopping List Schemas -----------------
class ShoppingItemCreate(BaseModel):
    ingredient_id: Optional[int] = None
    name: str = Field(..., min_length=1, max_length=100)
    quantity: float = Field(default=1.0, gt=0)
    unit: str = "pcs"
    notes: Optional[str] = None

class ShoppingItemOut(BaseModel):
    id: int
    ingredient_id: Optional[int]
    name: str
    quantity: float
    unit: str
    is_bought: bool
    is_from_warning: bool
    notes: Optional[str]
    created_at: datetime
    bought_at: Optional[datetime]

    class Config:
        from_attributes = True

class MarkBoughtRequest(BaseModel):
    update_inventory: bool = True
    actual_quantity: Optional[float] = None
    record_purchase: bool = False
    cost: Optional[float] = None


# ----------------- Dashboard & Predictor Schemas -----------------
class StockAlertItem(BaseModel):
    id: int
    name: str
    category: str
    quantity: float
    unit: str
    min_stock: float
    deficit: float

class ShortagePredictorStatus(BaseModel):
    status_label: str  # "Not enough data yet"
    days_recorded: int
    minimum_days_required: int = 30
    explanation: str
    ready_for_ml: bool
    data_summary: dict

class DashboardMetrics(BaseModel):
    # Sales
    sales_today: float
    sales_month: float
    sales_all_time: float
    sales_count_month: int

    # Purchases
    purchases_today: float
    purchases_month: float
    purchases_all_time: float
    purchases_count_month: int

    # Net: explicitly labeled Sales minus Purchases (NOT profit!)
    sales_minus_purchases_today: float
    sales_minus_purchases_month: float
    sales_minus_purchases_all_time: float

    # Stock
    total_ingredients_tracked: int
    low_stock_count: int
    stock_alerts: List[StockAlertItem]

    # Predictor
    shortage_predictor: ShortagePredictorStatus

    # Recent activity
    recent_sales: List[SaleOut]
    recent_purchases: List[PurchaseOut]
    recent_bakes: List[dict]
