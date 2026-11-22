from typing import List, Optional
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User, ShoppingItem, Ingredient, InventoryLog, Purchase, PurchaseItem
from backend.schemas import ShoppingItemCreate, ShoppingItemOut, MarkBoughtRequest
from backend.auth import get_current_user

router = APIRouter(prefix="/api/shopping", tags=["shopping"])

@router.get("", response_model=List[ShoppingItemOut])
def list_shopping_items(
    include_bought: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(ShoppingItem)
    if not include_bought:
        query = query.filter(ShoppingItem.is_bought == False)
    items = query.order_by(ShoppingItem.is_bought.asc(), ShoppingItem.created_at.desc()).all()
    return items

@router.post("", response_model=ShoppingItemOut, status_code=status.HTTP_201_CREATED)
def add_shopping_item(
    item_in: ShoppingItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    item = ShoppingItem(
        ingredient_id=item_in.ingredient_id,
        name=item_in.name.strip(),
        quantity=item_in.quantity,
        unit=item_in.unit.strip(),
        notes=item_in.notes,
        is_bought=False,
        is_from_warning=False
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

@router.post("/auto-add-low-stock")
def auto_add_low_stock(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Scans inventory for ingredients with quantity <= min_stock.
    Adds them to the shopping list if not already present unbought.
    Recommended restock amount: (min_stock * 2) - current_quantity.
    """
    low_stock_items = db.query(Ingredient).filter(Ingredient.quantity <= Ingredient.min_stock).all()

    added_items = []
    already_in_list = 0

    for ing in low_stock_items:
        # Check if already in unbought shopping list
        existing = db.query(ShoppingItem).filter(
            ShoppingItem.ingredient_id == ing.id,
            ShoppingItem.is_bought == False
        ).first()

        if existing:
            already_in_list += 1
            continue

        # Recommended restock amount
        needed = (ing.min_stock * 2) - ing.quantity
        if needed <= 0:
            needed = ing.min_stock or 1.0

        item = ShoppingItem(
            ingredient_id=ing.id,
            name=ing.name,
            quantity=round(needed, 2),
            unit=ing.unit,
            notes=f"Auto-added from low stock warning (Stock: {round(ing.quantity, 2)} {ing.unit}, Min: {round(ing.min_stock, 2)} {ing.unit})",
            is_bought=False,
            is_from_warning=True
        )
        db.add(item)
        added_items.append(ing.name)

    db.commit()

    return {
        "success": True,
        "added_count": len(added_items),
        "added_items": added_items,
        "already_in_list_count": already_in_list,
        "message": f"Added {len(added_items)} low-stock ingredient(s) to shopping list."
    }

@router.post("/{item_id}/mark-bought")
def mark_bought(
    item_id: int,
    req: MarkBoughtRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    item = db.query(ShoppingItem).filter(ShoppingItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Shopping item not found")

    item.is_bought = True
    item.bought_at = datetime.utcnow()

    bought_qty = req.actual_quantity if (req.actual_quantity is not None and req.actual_quantity > 0) else item.quantity

    stock_updated = False
    new_stock = None
    ing_name = item.name

    # Check if we should update inventory
    if req.update_inventory:
        target_ing = None
        if item.ingredient_id:
            target_ing = db.query(Ingredient).filter(Ingredient.id == item.ingredient_id).first()
        if not target_ing:
            target_ing = db.query(Ingredient).filter(Ingredient.name.ilike(item.name.strip())).first()

        if target_ing:
            old_qty = target_ing.quantity
            target_ing.quantity = old_qty + bought_qty
            new_stock = target_ing.quantity
            stock_updated = True
            ing_name = target_ing.name

            # Add to InventoryLog
            log = InventoryLog(
                ingredient_id=target_ing.id,
                ingredient_name=target_ing.name,
                change_type="SHOPPING_RESTOCK",
                quantity_delta=bought_qty,
                quantity_before=old_qty,
                quantity_after=target_ing.quantity,
                unit=target_ing.unit,
                reason=f"Restocked via shopping list item '{item.name}'"
            )
            db.add(log)

    # If requested to record as purchase expense
    purchase_created_id = None
    if req.record_purchase and req.cost and req.cost > 0:
        purchase = Purchase(
            bill_total=req.cost,
            date=date.today(),
            supplier="Shopping List Restock",
            notes=f"Purchased {bought_qty} {item.unit} of {item.name}"
        )
        db.add(purchase)
        db.flush()

        pi = PurchaseItem(
            purchase_id=purchase.id,
            ingredient_id=item.ingredient_id,
            item_name=item.name,
            quantity=bought_qty,
            unit=item.unit,
            cost=req.cost
        )
        db.add(pi)
        purchase_created_id = purchase.id

    db.commit()

    return {
        "success": True,
        "item_id": item.id,
        "is_bought": True,
        "stock_updated": stock_updated,
        "new_stock": round(new_stock, 2) if new_stock is not None else None,
        "purchase_id": purchase_created_id,
        "message": f"Marked '{item.name}' as bought." + (f" Updated stock of {ing_name} to {round(new_stock, 2)} {item.unit}." if stock_updated else "")
    }

@router.delete("/{item_id}")
def delete_shopping_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    item = db.query(ShoppingItem).filter(ShoppingItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Shopping item not found")

    db.delete(item)
    db.commit()
    return {"message": "Shopping item removed."}

@router.post("/clear-bought")
def clear_bought_items(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    count = db.query(ShoppingItem).filter(ShoppingItem.is_bought == True).delete()
    db.commit()
    return {"message": f"Cleared {count} bought items."}
