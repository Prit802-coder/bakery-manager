from datetime import date, datetime
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, distinct
from backend.database import get_db
from backend.models import User, Sale, Purchase, Ingredient, InventoryLog, BakeEvent
from backend.schemas import (
    DashboardMetrics, StockAlertItem, ShortagePredictorStatus,
    SaleOut, PurchaseOut
)
from backend.auth import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

@router.get("/metrics", response_model=DashboardMetrics)
def get_dashboard_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    today = date.today()
    current_year = today.year
    current_month = today.month

    # 1. SALES
    sales_today = db.query(func.coalesce(func.sum(Sale.amount), 0.0)).filter(Sale.date == today).scalar()
    sales_month_row = db.query(
        func.coalesce(func.sum(Sale.amount), 0.0),
        func.count(Sale.id)
    ).filter(
        extract("year", Sale.date) == current_year,
        extract("month", Sale.date) == current_month
    ).first()
    sales_month = sales_month_row[0]
    sales_count_month = sales_month_row[1]

    sales_all_time = db.query(func.coalesce(func.sum(Sale.amount), 0.0)).scalar()

    # 2. PURCHASES
    purchases_today = db.query(func.coalesce(func.sum(Purchase.bill_total), 0.0)).filter(Purchase.date == today).scalar()
    purchases_month_row = db.query(
        func.coalesce(func.sum(Purchase.bill_total), 0.0),
        func.count(Purchase.id)
    ).filter(
        extract("year", Purchase.date) == current_year,
        extract("month", Purchase.date) == current_month
    ).first()
    purchases_month = purchases_month_row[0]
    purchases_count_month = purchases_month_row[1]

    purchases_all_time = db.query(func.coalesce(func.sum(Purchase.bill_total), 0.0)).scalar()

    # 3. SALES MINUS PURCHASES (Explicitly NOT labeled as profit!)
    net_today = sales_today - purchases_today
    net_month = sales_month - purchases_month
    net_all_time = sales_all_time - purchases_all_time

    # 4. STOCK & RULE-BASED ALERTS
    all_ingredients = db.query(Ingredient).all()
    total_ingredients_tracked = len(all_ingredients)

    stock_alerts = []
    for ing in all_ingredients:
        if ing.quantity <= ing.min_stock:
            deficit = max(0.0, ing.min_stock - ing.quantity)
            stock_alerts.append(StockAlertItem(
                id=ing.id,
                name=ing.name,
                category=ing.category,
                quantity=round(ing.quantity, 2),
                unit=ing.unit,
                min_stock=round(ing.min_stock, 2),
                deficit=round(deficit, 2)
            ))

    low_stock_count = len(stock_alerts)

    # 5. MACHINE-LEARNING SHORTAGE PREDICTOR READINESS
    # Count distinct active days with real sales or bake logs
    sales_days = db.query(distinct(Sale.date)).count()
    bakes_days = db.query(distinct(BakeEvent.date)).count()
    unique_active_days = max(sales_days, bakes_days)
    minimum_days_required = 30
    ready_for_ml = unique_active_days >= minimum_days_required

    status_label = "Ready to train ML model" if ready_for_ml else "Not enough data yet"
    explanation = (
        f"Rule-based alerts are currently guarding your stock. "
        f"To train an accurate machine-learning shortage forecasting model without fabricated data, "
        f"at least {minimum_days_required} days of real baking and sales history are required. "
        f"Currently: {unique_active_days}/{minimum_days_required} days recorded."
    )

    predictor_status = ShortagePredictorStatus(
        status_label=status_label,
        days_recorded=unique_active_days,
        minimum_days_required=minimum_days_required,
        explanation=explanation,
        ready_for_ml=ready_for_ml,
        data_summary={
            "unique_active_days": unique_active_days,
            "total_sales_logged": db.query(func.count(Sale.id)).scalar(),
            "total_bakes_logged": db.query(func.count(BakeEvent.id)).scalar(),
            "total_inventory_logs": db.query(func.count(InventoryLog.id)).scalar()
        }
    )

    # 6. RECENT ACTIVITY
    recent_sales = db.query(Sale).order_by(Sale.date.desc(), Sale.id.desc()).limit(5).all()
    recent_purchases = db.query(Purchase).order_by(Purchase.date.desc(), Purchase.id.desc()).limit(5).all()

    recent_bakes_rows = db.query(BakeEvent).order_by(BakeEvent.created_at.desc()).limit(5).all()
    recent_bakes = [
        {
            "id": b.id,
            "recipe_name": b.recipe_name,
            "multiplier": b.multiplier,
            "date": str(b.date),
            "created_at": b.created_at.isoformat() if b.created_at else None,
            "notes": b.notes
        }
        for b in recent_bakes_rows
    ]

    return DashboardMetrics(
        sales_today=round(sales_today, 2),
        sales_month=round(sales_month, 2),
        sales_all_time=round(sales_all_time, 2),
        sales_count_month=sales_count_month,
        purchases_today=round(purchases_today, 2),
        purchases_month=round(purchases_month, 2),
        purchases_all_time=round(purchases_all_time, 2),
        purchases_count_month=purchases_count_month,
        sales_minus_purchases_today=round(net_today, 2),
        sales_minus_purchases_month=round(net_month, 2),
        sales_minus_purchases_all_time=round(net_all_time, 2),
        total_ingredients_tracked=total_ingredients_tracked,
        low_stock_count=low_stock_count,
        stock_alerts=stock_alerts,
        shortage_predictor=predictor_status,
        recent_sales=recent_sales,
        recent_purchases=recent_purchases,
        recent_bakes=recent_bakes
    )
