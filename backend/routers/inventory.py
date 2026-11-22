from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User, Ingredient, InventoryLog
from backend.schemas import (
    IngredientCreate, IngredientUpdate, IngredientOut,
    IngredientStockAdjust, InventoryLogOut
)
from backend.auth import get_current_user

router = APIRouter(prefix="/api/inventory", tags=["inventory"])

@router.get("", response_model=List[IngredientOut])
def list_ingredients(
    search: Optional[str] = None,
    category: Optional[str] = None,
    low_stock_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Ingredient)
    if search:
        query = query.filter(Ingredient.name.ilike(f"%{search.strip()}%"))
    if category and category.lower() != "all":
        query = query.filter(Ingredient.category.ilike(f"%{category.strip()}%"))

    ingredients = query.order_by(Ingredient.name.asc()).all()

    results = []
    for item in ingredients:
        is_low = (item.quantity <= item.min_stock)
        if low_stock_only and not is_low:
            continue
        out = IngredientOut(
            id=item.id,
            name=item.name,
            category=item.category,
            quantity=round(item.quantity, 2),
            unit=item.unit,
            min_stock=round(item.min_stock, 2),
            cost_per_unit=item.cost_per_unit,
            notes=item.notes,
            is_low_stock=is_low,
            created_at=item.created_at,
            updated_at=item.updated_at
        )
        results.append(out)

    return results

@router.get("/logs", response_model=List[InventoryLogOut])
def get_inventory_logs(
    ingredient_id: Optional[int] = None,
    change_type: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(InventoryLog)
    if ingredient_id:
        query = query.filter(InventoryLog.ingredient_id == ingredient_id)
    if change_type:
        query = query.filter(InventoryLog.change_type == change_type)

    logs = query.order_by(InventoryLog.created_at.desc()).limit(limit).all()
    return logs

@router.get("/{ingredient_id}", response_model=IngredientOut)
def get_ingredient(
    ingredient_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    item = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    return IngredientOut(
        id=item.id,
        name=item.name,
        category=item.category,
        quantity=round(item.quantity, 2),
        unit=item.unit,
        min_stock=round(item.min_stock, 2),
        cost_per_unit=item.cost_per_unit,
        notes=item.notes,
        is_low_stock=(item.quantity <= item.min_stock),
        created_at=item.created_at,
        updated_at=item.updated_at
    )

@router.post("", response_model=IngredientOut, status_code=status.HTTP_201_CREATED)
def create_ingredient(
    item_in: IngredientCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    existing = db.query(Ingredient).filter(Ingredient.name.ilike(item_in.name.strip())).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Ingredient '{item_in.name}' already exists.")

    ingredient = Ingredient(
        name=item_in.name.strip(),
        category=item_in.category.strip() if item_in.category else "General",
        quantity=item_in.quantity,
        unit=item_in.unit.strip(),
        min_stock=item_in.min_stock,
        cost_per_unit=item_in.cost_per_unit or 0.0,
        notes=item_in.notes
    )
    db.add(ingredient)
    db.flush()

    # Log initial inventory balance
    if ingredient.quantity > 0:
        log = InventoryLog(
            ingredient_id=ingredient.id,
            ingredient_name=ingredient.name,
            change_type="MANUAL_ADJUSTMENT",
            quantity_delta=ingredient.quantity,
            quantity_before=0.0,
            quantity_after=ingredient.quantity,
            unit=ingredient.unit,
            reason="Initial stock entry"
        )
        db.add(log)

    db.commit()
    db.refresh(ingredient)

    return IngredientOut(
        id=ingredient.id,
        name=ingredient.name,
        category=ingredient.category,
        quantity=round(ingredient.quantity, 2),
        unit=ingredient.unit,
        min_stock=round(ingredient.min_stock, 2),
        cost_per_unit=ingredient.cost_per_unit,
        notes=ingredient.notes,
        is_low_stock=(ingredient.quantity <= ingredient.min_stock),
        created_at=ingredient.created_at,
        updated_at=ingredient.updated_at
    )

@router.put("/{ingredient_id}", response_model=IngredientOut)
def update_ingredient(
    ingredient_id: int,
    item_in: IngredientUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    item = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    if item_in.name and item_in.name.strip().lower() != item.name.lower():
        existing = db.query(Ingredient).filter(
            Ingredient.name.ilike(item_in.name.strip()),
            Ingredient.id != ingredient_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Ingredient '{item_in.name}' already exists.")
        item.name = item_in.name.strip()

    if item_in.category is not None:
        item.category = item_in.category.strip()
    if item_in.unit is not None:
        item.unit = item_in.unit.strip()
    if item_in.min_stock is not None:
        item.min_stock = item_in.min_stock
    if item_in.cost_per_unit is not None:
        item.cost_per_unit = item_in.cost_per_unit
    if item_in.notes is not None:
        item.notes = item_in.notes

    # If quantity was directly updated here
    if item_in.quantity is not None and item_in.quantity != item.quantity:
        delta = item_in.quantity - item.quantity
        log = InventoryLog(
            ingredient_id=item.id,
            ingredient_name=item.name,
            change_type="MANUAL_ADJUSTMENT",
            quantity_delta=delta,
            quantity_before=item.quantity,
            quantity_after=item_in.quantity,
            unit=item.unit,
            reason="Direct stock count correction"
        )
        db.add(log)
        item.quantity = item_in.quantity

    db.commit()
    db.refresh(item)

    return IngredientOut(
        id=item.id,
        name=item.name,
        category=item.category,
        quantity=round(item.quantity, 2),
        unit=item.unit,
        min_stock=round(item.min_stock, 2),
        cost_per_unit=item.cost_per_unit,
        notes=item.notes,
        is_low_stock=(item.quantity <= item.min_stock),
        created_at=item.created_at,
        updated_at=item.updated_at
    )

@router.post("/{ingredient_id}/adjust", response_model=IngredientOut)
def adjust_stock(
    ingredient_id: int,
    adj: IngredientStockAdjust,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    item = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    new_quantity = item.quantity + adj.quantity_delta
    if new_quantity < 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reduce stock below zero. Current stock is {item.quantity} {item.unit}."
        )

    log = InventoryLog(
        ingredient_id=item.id,
        ingredient_name=item.name,
        change_type=adj.change_type,
        quantity_delta=adj.quantity_delta,
        quantity_before=item.quantity,
        quantity_after=new_quantity,
        unit=item.unit,
        reason=adj.reason or f"Stock adjustment ({adj.change_type})"
    )
    db.add(log)
    item.quantity = new_quantity
    db.commit()
    db.refresh(item)

    return IngredientOut(
        id=item.id,
        name=item.name,
        category=item.category,
        quantity=round(item.quantity, 2),
        unit=item.unit,
        min_stock=round(item.min_stock, 2),
        cost_per_unit=item.cost_per_unit,
        notes=item.notes,
        is_low_stock=(item.quantity <= item.min_stock),
        created_at=item.created_at,
        updated_at=item.updated_at
    )

@router.delete("/{ingredient_id}")
def delete_ingredient(
    ingredient_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    item = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    db.delete(item)
    db.commit()
    return {"message": f"Ingredient '{item.name}' deleted successfully."}
