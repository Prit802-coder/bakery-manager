import csv
import io
from datetime import date
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User, Sale, Purchase, Ingredient, InventoryLog
from backend.auth import get_current_user

router = APIRouter(prefix="/api/exports", tags=["exports"])

@router.get("/sales.csv")
def export_sales_csv(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    sales = db.query(Sale).order_by(Sale.date.desc(), Sale.id.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Sale ID", "Date", "Cake Type", "Quantity", "Amount (Rs)",
        "Customer Name", "Payment Method", "Notes", "Logged At"
    ])

    for s in sales:
        writer.writerow([
            s.id,
            s.date.isoformat() if s.date else "",
            s.cake_type,
            s.quantity,
            f"{s.amount:.2f}",
            s.customer_name or "",
            s.payment_method or "",
            s.notes or "",
            s.created_at.strftime("%Y-%m-%d %H:%M:%S") if s.created_at else ""
        ])

    csv_content = output.getvalue()
    filename = f"sales_records_{date.today().isoformat()}.csv"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.get("/purchases.csv")
def export_purchases_csv(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    purchases = db.query(Purchase).order_by(Purchase.date.desc(), Purchase.id.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Purchase ID", "Date", "Bill Total (Rs)", "Supplier / Store",
        "Item Details", "Notes", "Logged At"
    ])

    for p in purchases:
        items_summary = "; ".join([
            f"{it.item_name} ({it.quantity} {it.unit} @ Rs.{it.cost:.2f})"
            for it in p.items
        ])
        writer.writerow([
            p.id,
            p.date.isoformat() if p.date else "",
            f"{p.bill_total:.2f}",
            p.supplier or "",
            items_summary,
            p.notes or "",
            p.created_at.strftime("%Y-%m-%d %H:%M:%S") if p.created_at else ""
        ])

    csv_content = output.getvalue()
    filename = f"purchase_records_{date.today().isoformat()}.csv"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.get("/inventory.csv")
def export_inventory_csv(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ingredients = db.query(Ingredient).order_by(Ingredient.category.asc(), Ingredient.name.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Ingredient ID", "Name", "Category", "Current Stock", "Unit",
        "Min Stock Threshold", "Stock Status", "Cost Per Unit (Rs)", "Notes", "Last Updated"
    ])

    for i in ingredients:
        status = "LOW STOCK WARNING" if i.quantity <= i.min_stock else "Adequate"
        writer.writerow([
            i.id,
            i.name,
            i.category,
            f"{i.quantity:.2f}",
            i.unit,
            f"{i.min_stock:.2f}",
            status,
            f"{i.cost_per_unit:.2f}" if i.cost_per_unit else "0.00",
            i.notes or "",
            i.updated_at.strftime("%Y-%m-%d %H:%M:%S") if i.updated_at else ""
        ])

    csv_content = output.getvalue()
    filename = f"inventory_status_{date.today().isoformat()}.csv"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.get("/inventory-logs.csv")
def export_inventory_logs_csv(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logs = db.query(InventoryLog).order_by(InventoryLog.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Log ID", "Date & Time", "Ingredient", "Change Type",
        "Delta", "Stock Before", "Stock After", "Unit", "Reason / Reference"
    ])

    for l in logs:
        writer.writerow([
            l.id,
            l.created_at.strftime("%Y-%m-%d %H:%M:%S") if l.created_at else "",
            l.ingredient_name,
            l.change_type,
            f"{l.quantity_delta:+.2f}",
            f"{l.quantity_before:.2f}",
            f"{l.quantity_after:.2f}",
            l.unit,
            l.reason or ""
        ])

    csv_content = output.getvalue()
    filename = f"stock_history_logs_{date.today().isoformat()}.csv"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
