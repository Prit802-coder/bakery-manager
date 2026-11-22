from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from backend.database import get_db
from backend.models import User, Purchase, PurchaseItem, Ingredient, InventoryLog
from backend.schemas import (
    PurchaseCreate, PurchaseUpdate, PurchaseOut, PurchasesSummary, DailySummary, MonthlySummary
)
from backend.auth import get_current_user

router = APIRouter(prefix="/api/purchases", tags=["purchases"])

@router.get("", response_model=List[PurchaseOut])
def list_purchases(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    supplier: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Purchase)
    if start_date:
        query = query.filter(Purchase.date >= start_date)
    if end_date:
        query = query.filter(Purchase.date <= end_date)
    if supplier:
        query = query.filter(Purchase.supplier.ilike(f"%{supplier.strip()}%"))

    purchases = query.order_by(Purchase.date.desc(), Purchase.id.desc()).limit(limit).all()
    return purchases

@router.get("/summary", response_model=PurchasesSummary)
def get_purchases_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    today = date.today()
    current_year = today.year
    current_month = today.month

    # Today's total & count
    today_row = db.query(
        func.coalesce(func.sum(Purchase.bill_total), 0.0),
        func.count(Purchase.id)
    ).filter(Purchase.date == today).first()
    today_total = float(today_row[0])
    today_count = int(today_row[1])

    # This month's total & count
    month_row = db.query(
        func.coalesce(func.sum(Purchase.bill_total), 0.0),
        func.count(Purchase.id)
    ).filter(
        extract("year", Purchase.date) == current_year,
        extract("month", Purchase.date) == current_month
    ).first()
    month_total = float(month_row[0])
    month_count = int(month_row[1])

    # All-time total & count
    all_row = db.query(
        func.coalesce(func.sum(Purchase.bill_total), 0.0),
        func.count(Purchase.id)
    ).first()
    all_time_total = float(all_row[0])
    all_time_count = int(all_row[1])

    # Daily breakdown for recent 30 days
    daily_rows = db.query(
        Purchase.date,
        func.sum(Purchase.bill_total),
        func.count(Purchase.id)
    ).group_by(Purchase.date).order_by(Purchase.date.desc()).limit(30).all()

    daily_breakdown = [
        DailySummary(
            date=str(row[0]),
            total_amount=round(float(row[1]), 2),
            count=int(row[2])
        )
        for row in daily_rows
    ]

    # Monthly breakdown
    monthly_rows = db.query(
        func.strftime("%Y-%m", Purchase.date).label("month"),
        func.sum(Purchase.bill_total),
        func.count(Purchase.id)
    ).group_by("month").order_by(func.strftime("%Y-%m", Purchase.date).desc()).limit(12).all()

    monthly_breakdown = [
        MonthlySummary(
            month=str(row[0]),
            total_amount=round(float(row[1]), 2),
            count=int(row[2])
        )
        for row in monthly_rows
    ]

    return PurchasesSummary(
        today_total=round(today_total, 2),
        today_count=today_count,
        this_month_total=round(month_total, 2),
        this_month_count=month_count,
        all_time_total=round(all_time_total, 2),
        all_time_count=all_time_count,
        daily_breakdown=daily_breakdown,
        monthly_breakdown=monthly_breakdown
    )

@router.post("", response_model=PurchaseOut, status_code=status.HTTP_201_CREATED)
def record_purchase(
    purchase_in: PurchaseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    purchase = Purchase(
        bill_total=purchase_in.bill_total,
        date=purchase_in.date,
        supplier=purchase_in.supplier.strip() if purchase_in.supplier else None,
        notes=purchase_in.notes
    )
    db.add(purchase)
    db.flush()

    if purchase_in.items:
        for it in purchase_in.items:
            pi = PurchaseItem(
                purchase_id=purchase.id,
                ingredient_id=it.ingredient_id,
                item_name=it.item_name.strip(),
                quantity=it.quantity,
                unit=it.unit.strip(),
                cost=it.cost
            )
            db.add(pi)

            # If user elected to update inventory stock
            if purchase_in.update_inventory_stock:
                matched_ing = None
                if it.ingredient_id:
                    matched_ing = db.query(Ingredient).filter(Ingredient.id == it.ingredient_id).first()
                elif it.item_name:
                    matched_ing = db.query(Ingredient).filter(Ingredient.name.ilike(it.item_name.strip())).first()

                if matched_ing:
                    old_qty = matched_ing.quantity
                    new_qty = old_qty + it.quantity
                    matched_ing.quantity = new_qty

                    # Log restock
                    log = InventoryLog(
                        ingredient_id=matched_ing.id,
                        ingredient_name=matched_ing.name,
                        change_type="RESTOCK_PURCHASE",
                        quantity_delta=it.quantity,
                        quantity_before=old_qty,
                        quantity_after=new_qty,
                        unit=matched_ing.unit,
                        reason=f"Purchase bill #{purchase.id} from {purchase.supplier or 'Store'}"
                    )
                    db.add(log)

    db.commit()
    db.refresh(purchase)
    return purchase

@router.get("/{purchase_id}", response_model=PurchaseOut)
def get_purchase(
    purchase_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    purchase = db.query(Purchase).filter(Purchase.id == purchase_id).first()
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase not found")
    return purchase

@router.put("/{purchase_id}", response_model=PurchaseOut)
def update_purchase(
    purchase_id: int,
    purchase_in: PurchaseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    purchase = db.query(Purchase).filter(Purchase.id == purchase_id).first()
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase not found")

    if purchase_in.bill_total is not None:
        purchase.bill_total = purchase_in.bill_total
    if purchase_in.date is not None:
        purchase.date = purchase_in.date
    if purchase_in.supplier is not None:
        purchase.supplier = purchase_in.supplier.strip()
    if purchase_in.notes is not None:
        purchase.notes = purchase_in.notes

    db.commit()
    db.refresh(purchase)
    return purchase

@router.delete("/{purchase_id}")
def delete_purchase(
    purchase_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    purchase = db.query(Purchase).filter(Purchase.id == purchase_id).first()
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase not found")

    db.delete(purchase)
    db.commit()
    return {"message": "Purchase record deleted successfully."}
