from typing import List, Optional
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from backend.database import get_db
from backend.models import User, Sale
from backend.schemas import (
    SaleCreate, SaleUpdate, SaleOut, SalesSummary, DailySummary, MonthlySummary
)
from backend.auth import get_current_user

router = APIRouter(prefix="/api/sales", tags=["sales"])

@router.get("", response_model=List[SaleOut])
def list_sales(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    cake_type: Optional[str] = None,
    payment_method: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Sale)
    if start_date:
        query = query.filter(Sale.date >= start_date)
    if end_date:
        query = query.filter(Sale.date <= end_date)
    if cake_type:
        query = query.filter(Sale.cake_type.ilike(f"%{cake_type.strip()}%"))
    if payment_method and payment_method.lower() != "all":
        query = query.filter(Sale.payment_method == payment_method)

    sales = query.order_by(Sale.date.desc(), Sale.id.desc()).limit(limit).all()
    return sales

@router.get("/summary", response_model=SalesSummary)
def get_sales_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    today = date.today()
    current_year = today.year
    current_month = today.month

    # Today's total & count
    today_sales = db.query(
        func.coalesce(func.sum(Sale.amount), 0.0),
        func.count(Sale.id)
    ).filter(Sale.date == today).first()
    today_total = float(today_sales[0])
    today_count = int(today_sales[1])

    # This month's total & count
    month_sales = db.query(
        func.coalesce(func.sum(Sale.amount), 0.0),
        func.count(Sale.id)
    ).filter(
        extract("year", Sale.date) == current_year,
        extract("month", Sale.date) == current_month
    ).first()
    month_total = float(month_sales[0])
    month_count = int(month_sales[1])

    # All-time total & count
    all_sales = db.query(
        func.coalesce(func.sum(Sale.amount), 0.0),
        func.count(Sale.id)
    ).first()
    all_time_total = float(all_sales[0])
    all_time_count = int(all_sales[1])

    # Daily breakdown for recent 30 days
    daily_rows = db.query(
        Sale.date,
        func.sum(Sale.amount),
        func.count(Sale.id)
    ).group_by(Sale.date).order_by(Sale.date.desc()).limit(30).all()

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
        func.strftime("%Y-%m", Sale.date).label("month"),
        func.sum(Sale.amount),
        func.count(Sale.id)
    ).group_by("month").order_by(func.strftime("%Y-%m", Sale.date).desc()).limit(12).all()

    monthly_breakdown = [
        MonthlySummary(
            month=str(row[0]),
            total_amount=round(float(row[1]), 2),
            count=int(row[2])
        )
        for row in monthly_rows
    ]

    return SalesSummary(
        today_total=round(today_total, 2),
        today_count=today_count,
        this_month_total=round(month_total, 2),
        this_month_count=month_count,
        all_time_total=round(all_time_total, 2),
        all_time_count=all_time_count,
        daily_breakdown=daily_breakdown,
        monthly_breakdown=monthly_breakdown
    )

@router.post("", response_model=SaleOut, status_code=status.HTTP_201_CREATED)
def record_sale(
    sale_in: SaleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    sale = Sale(
        cake_type=sale_in.cake_type.strip(),
        quantity=sale_in.quantity,
        amount=sale_in.amount,
        date=sale_in.date,
        customer_name=sale_in.customer_name.strip() if sale_in.customer_name else None,
        payment_method=sale_in.payment_method or "Cash",
        notes=sale_in.notes
    )
    db.add(sale)
    db.commit()
    db.refresh(sale)
    return sale

@router.get("/{sale_id}", response_model=SaleOut)
def get_sale(
    sale_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    return sale

@router.put("/{sale_id}", response_model=SaleOut)
def update_sale(
    sale_id: int,
    sale_in: SaleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")

    if sale_in.cake_type is not None:
        sale.cake_type = sale_in.cake_type.strip()
    if sale_in.quantity is not None:
        sale.quantity = sale_in.quantity
    if sale_in.amount is not None:
        sale.amount = sale_in.amount
    if sale_in.date is not None:
        sale.date = sale_in.date
    if sale_in.customer_name is not None:
        sale.customer_name = sale_in.customer_name.strip()
    if sale_in.payment_method is not None:
        sale.payment_method = sale_in.payment_method
    if sale_in.notes is not None:
        sale.notes = sale_in.notes

    db.commit()
    db.refresh(sale)
    return sale

@router.delete("/{sale_id}")
def delete_sale(
    sale_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")

    db.delete(sale)
    db.commit()
    return {"message": "Sale record deleted successfully."}
