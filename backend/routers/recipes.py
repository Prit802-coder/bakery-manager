from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User, Recipe, RecipeIngredient, Ingredient, InventoryLog, BakeEvent
from backend.schemas import (
    RecipeCreate, RecipeUpdate, RecipeOut, RecipeIngredientDetail,
    BakePreviewResponse, BakeIngredientRequirement, BakeConfirmRequest
)
from backend.auth import get_current_user

router = APIRouter(prefix="/api/recipes", tags=["recipes"])

def convert_amount(amount: float, from_unit: str, to_unit: str) -> float:
    """Helper to convert common weight and volume units between recipe and inventory."""
    fu = from_unit.strip().lower()
    tu = to_unit.strip().lower()

    if fu == tu:
        return amount

    # Weight conversions
    if fu == "g" and tu == "kg":
        return amount / 1000.0
    if fu == "kg" and tu == "g":
        return amount * 1000.0

    # Volume conversions
    if fu == "ml" and tu == "l":
        return amount / 1000.0
    if fu == "l" and tu == "ml":
        return amount * 1000.0

    # Teaspoon / Tablespoon to grams approximate for baking
    if fu == "tsp" and tu == "g":
        return amount * 5.0
    if fu == "tbsp" and tu == "g":
        return amount * 15.0

    # Default to direct amount if units are same category or custom (e.g. pcs, cups)
    return amount

def format_recipe_out(r: Recipe) -> RecipeOut:
    ing_details = []
    for ri in r.ingredients:
        ing = ri.ingredient
        current_stock = ing.quantity if ing else 0.0
        stock_unit = ing.unit if ing else ri.unit
        name = ing.name if ing else f"Ingredient #{ri.ingredient_id}"
        ing_details.append(RecipeIngredientDetail(
            id=ri.id,
            ingredient_id=ri.ingredient_id,
            ingredient_name=name,
            amount=ri.amount,
            unit=ri.unit,
            current_stock=round(current_stock, 2),
            stock_unit=stock_unit
        ))

    return RecipeOut(
        id=r.id,
        name=r.name,
        category=r.category,
        yield_quantity=r.yield_quantity,
        yield_unit=r.yield_unit,
        instructions=r.instructions,
        ingredients=ing_details,
        created_at=r.created_at
    )

@router.get("", response_model=List[RecipeOut])
def list_recipes(
    search: Optional[str] = None,
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Recipe)
    if search:
        query = query.filter(Recipe.name.ilike(f"%{search.strip()}%"))
    if category and category.lower() != "all":
        query = query.filter(Recipe.category.ilike(f"%{category.strip()}%"))

    recipes = query.order_by(Recipe.name.asc()).all()
    return [format_recipe_out(r) for r in recipes]

@router.get("/{recipe_id}", response_model=RecipeOut)
def get_recipe(
    recipe_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return format_recipe_out(recipe)

@router.post("", response_model=RecipeOut, status_code=status.HTTP_201_CREATED)
def create_recipe(
    recipe_in: RecipeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    existing = db.query(Recipe).filter(Recipe.name.ilike(recipe_in.name.strip())).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Recipe '{recipe_in.name}' already exists.")

    recipe = Recipe(
        name=recipe_in.name.strip(),
        category=recipe_in.category.strip() if recipe_in.category else "Cakes",
        yield_quantity=recipe_in.yield_quantity,
        yield_unit=recipe_in.yield_unit.strip(),
        instructions=recipe_in.instructions
    )
    db.add(recipe)
    db.flush()

    for item in recipe_in.ingredients:
        # Check ingredient exists
        ing = db.query(Ingredient).filter(Ingredient.id == item.ingredient_id).first()
        if not ing:
            raise HTTPException(status_code=400, detail=f"Ingredient ID {item.ingredient_id} not found.")

        ri = RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=item.ingredient_id,
            amount=item.amount,
            unit=item.unit.strip()
        )
        db.add(ri)

    db.commit()
    db.refresh(recipe)
    return format_recipe_out(recipe)

@router.put("/{recipe_id}", response_model=RecipeOut)
def update_recipe(
    recipe_id: int,
    recipe_in: RecipeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    if recipe_in.name and recipe_in.name.strip().lower() != recipe.name.lower():
        existing = db.query(Recipe).filter(
            Recipe.name.ilike(recipe_in.name.strip()),
            Recipe.id != recipe_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Recipe '{recipe_in.name}' already exists.")
        recipe.name = recipe_in.name.strip()

    if recipe_in.category is not None:
        recipe.category = recipe_in.category.strip()
    if recipe_in.yield_quantity is not None:
        recipe.yield_quantity = recipe_in.yield_quantity
    if recipe_in.yield_unit is not None:
        recipe.yield_unit = recipe_in.yield_unit.strip()
    if recipe_in.instructions is not None:
        recipe.instructions = recipe_in.instructions

    if recipe_in.ingredients is not None:
        # Remove old ingredients and add new
        db.query(RecipeIngredient).filter(RecipeIngredient.recipe_id == recipe.id).delete()
        for item in recipe_in.ingredients:
            ri = RecipeIngredient(
                recipe_id=recipe.id,
                ingredient_id=item.ingredient_id,
                amount=item.amount,
                unit=item.unit.strip()
            )
            db.add(ri)

    db.commit()
    db.refresh(recipe)
    return format_recipe_out(recipe)

@router.delete("/{recipe_id}")
def delete_recipe(
    recipe_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    db.delete(recipe)
    db.commit()
    return {"message": f"Recipe '{recipe.name}' deleted successfully."}

# ==========================================
# BAKE PREVIEW & CONFIRM WORKFLOW
# ==========================================
@router.get("/{recipe_id}/bake-preview", response_model=BakePreviewResponse)
def preview_bake(
    recipe_id: int,
    multiplier: float = Query(1.0, gt=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Calculates exact ingredient amounts for the requested batch,
    compares against current inventory, and flags any shortages.
    Does NOT deduct stock.
    """
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    items = []
    warnings = []
    can_bake = True

    yield_desc = f"{recipe.yield_quantity * multiplier:g} {recipe.yield_unit}"

    for ri in recipe.ingredients:
        ing = ri.ingredient
        if not ing:
            continue

        required_recipe_units = ri.amount * multiplier
        # Convert to ingredient's inventory unit
        deduction_in_stock_unit = convert_amount(required_recipe_units, ri.unit, ing.unit)
        stock_after = ing.quantity - deduction_in_stock_unit
        is_sufficient = (stock_after >= 0)

        if not is_sufficient:
            can_bake = False
            shortage = round(deduction_in_stock_unit - ing.quantity, 2)
            warnings.append(
                f"Short on '{ing.name}': Need {round(deduction_in_stock_unit, 2)} {ing.unit}, but only {round(ing.quantity, 2)} {ing.unit} in stock (Deficit: {shortage} {ing.unit})."
            )
        elif stock_after <= ing.min_stock:
            warnings.append(
                f"Stock warning for '{ing.name}': Will drop to {round(stock_after, 2)} {ing.unit} (Below minimum threshold of {ing.min_stock} {ing.unit})."
            )

        items.append(BakeIngredientRequirement(
            ingredient_id=ing.id,
            ingredient_name=ing.name,
            required_amount=round(deduction_in_stock_unit, 2),
            unit=ing.unit,
            current_stock=round(ing.quantity, 2),
            stock_unit=ing.unit,
            is_sufficient=is_sufficient,
            stock_after_bake=round(max(0.0, stock_after), 2)
        ))

    return BakePreviewResponse(
        recipe_id=recipe.id,
        recipe_name=recipe.name,
        multiplier=multiplier,
        yield_description=yield_desc,
        can_bake=can_bake,
        items=items,
        warnings=warnings
    )

@router.post("/{recipe_id}/bake-confirm")
def confirm_bake(
    recipe_id: int,
    req: BakeConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Owner confirms bake.
    Subtracts calculated ingredients from inventory,
    logs every change in InventoryLog, and creates a BakeEvent.
    """
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    multiplier = req.multiplier
    bake_date = req.bake_date or date.today()

    deductions_summary = []

    # First pass: check availability
    for ri in recipe.ingredients:
        ing = ri.ingredient
        if not ing:
            continue
        required_in_recipe_unit = ri.amount * multiplier
        deduction_in_stock_unit = convert_amount(required_in_recipe_unit, ri.unit, ing.unit)

        if ing.quantity < deduction_in_stock_unit:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot confirm bake: Insufficient '{ing.name}'. Required: {round(deduction_in_stock_unit, 2)} {ing.unit}, Available: {round(ing.quantity, 2)} {ing.unit}."
            )

    # Second pass: execute stock deduction & logging
    for ri in recipe.ingredients:
        ing = ri.ingredient
        if not ing:
            continue
        required_in_recipe_unit = ri.amount * multiplier
        deduction_in_stock_unit = convert_amount(required_in_recipe_unit, ri.unit, ing.unit)

        old_qty = ing.quantity
        new_qty = old_qty - deduction_in_stock_unit
        ing.quantity = new_qty

        # Record inventory change log
        log = InventoryLog(
            ingredient_id=ing.id,
            ingredient_name=ing.name,
            change_type="BAKE_USAGE",
            quantity_delta=-round(deduction_in_stock_unit, 2),
            quantity_before=round(old_qty, 2),
            quantity_after=round(new_qty, 2),
            unit=ing.unit,
            reason=f"Baked {multiplier:g}x {recipe.name}"
        )
        db.add(log)

        deductions_summary.append({
            "ingredient": ing.name,
            "deducted": round(deduction_in_stock_unit, 2),
            "unit": ing.unit,
            "remaining": round(new_qty, 2)
        })

    # Record Bake Event
    bake_event = BakeEvent(
        recipe_id=recipe.id,
        recipe_name=recipe.name,
        multiplier=multiplier,
        date=bake_date,
        notes=req.notes or f"Baked {multiplier:g}x {recipe.name}"
    )
    db.add(bake_event)

    db.commit()

    return {
        "success": True,
        "message": f"Successfully recorded baking {multiplier:g}x '{recipe.name}'. Ingredients deducted from stock.",
        "recipe_name": recipe.name,
        "multiplier": multiplier,
        "date": str(bake_date),
        "deductions": deductions_summary
    }
