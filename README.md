# 🎂 Mom's Homemade Cake Business Manager

A private, mobile-first web app designed specifically for a homemade cake baker selling in person. It provides a simple, touch-friendly interface on her phone to log sales, track ingredient purchases, manage recipe-driven stock deductions, maintain an automated shopping list, and export business CSV records.

> **Privacy & Scope Note:**  
> This app is strictly private for the owner. It has **no public menu or online ordering**, designed exclusively for in-person homemade cake operations.

---

## 📱 Highlights & Phone-Friendly Design

- **Mobile-First UX:** Bottom navigation bar, minimum 48px touch targets, numeric keypads (`inputmode="decimal"`) for fast number entry with thumbs while in the kitchen.
- **Warm Bakery Palette:** Soft cream background, terracotta accents, clear legible typography.
- **Private Single-Owner Login:** Secured with bcrypt password hashing and persistent 30-day JWT tokens so mom doesn't need to re-login every time she opens her phone browser.
- **Strict Cash Flow Transparency:** Dashboard displays **"Sales minus Purchases"**, explicitly *not* labeled as profit.
- **Safe Recipe-Driven Stock Deductions:** When mom bakes a cake, she selects the batch size, reviews the ingredients required vs available stock, and must **confirm before any stock is deducted**.
- **Rule-Based Alerts & ML-Ready Foundation:** Live alerts for ingredients at or below threshold. Dated sales and stock usage are systematically logged. The AI/ML Shortage Predictor card shows **"Not enough data yet"** until 30 days of real history have elapsed, preventing fabricated predictions.
- **One-Click CSV Exports:** Direct CSV downloads for Sales, Purchases, Inventory Status, and Stock Audit History.

---

## 🛠️ Tech Stack Rationale

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Backend API** | Python FastAPI | High-performance, automatic input validation with Pydantic, clean RESTful endpoints, zero overhead. |
| **Database** | SQLite + SQLAlchemy | Reliable, zero-configuration embedded SQL database stored in a single file (`cake_business.db`), perfectly suited for a private local business. |
| **Authentication** | Passlib / Bcrypt + python-jose | Industry-standard secure password hashing and 30-day JWT sessions. |
| **Frontend** | Responsive Vanilla JS + Mobile CSS | Fast, lightweight single-page app (SPA) with zero heavy build steps, instantly served by FastAPI. Completely self-contained. |

---

## 🚀 Quick Setup & Run Instructions

### 1. Requirements
Ensure Python 3.10+ is installed on your computer.

### 2. Install Dependencies
Run the following in the project folder:
```bash
pip install -r requirements.txt
```

*(Note: If you already have `fastapi`, `uvicorn`, `sqlalchemy`, `pydantic`, `bcrypt`, `python-jose` installed, you can skip straight to step 3).*

### 3. Configure Your Environment Variables
Copy the example environment file and configure your private credentials:
```bash
cp .env.example .env
```
Open `.env` to set your desired initial owner credentials:
```bash
OWNER_USERNAME=mom
OWNER_PASSWORD=your_secure_password_here
```
*(Note: If `OWNER_PASSWORD` is not set, a secure random password will be generated automatically and saved to `.env`).*

### 4. Start the Application
Run the launcher script:
```bash
python run.py
```
*(or via npm: `npm start`)*

This automatically initializes the database tables, applies your credentials from `.env`, and prints your local URLs:
```
============================================================
  MOM'S HOMEMADE CAKE BUSINESS MANAGER
  Private, Phone-Friendly Bakery Management System
============================================================

[OK] Application is ready!
 -> Access on this computer: http://localhost:8000
 -> Access on Mom's Phone (same Wi-Fi): http://192.168.1.9:8000

Owner Authentication:
   Username: mom
   Password: [Configured in your private .env file (OWNER_PASSWORD)]
============================================================
```

---

## 📲 How Mom Can Use It On Her Phone

1. Connect Mom's smartphone to the **same home Wi-Fi network** as the computer running `run.py`.
2. Open Chrome or Safari on the phone and go to:
   ```
   http://<YOUR-IP>:8000
   ```
   *(e.g., `http://192.168.1.9:8000`)*
3. **Log in:**
   - **Username:** `mom` (or value set in `OWNER_USERNAME`)
   - **Password:** The password configured in your private `.env` file
4. **Tip (Add to Home Screen):**
   - **On iPhone (Safari):** Tap the Share icon -> tap **"Add to Home Screen"**. It will appear like a native mobile app!
   - **On Android (Chrome):** Tap the 3 dots menu -> tap **"Add to Home screen"** or **"Install app"**.

---

## 📋 Features Walkthrough

### 1. 📊 Dashboard
- **Sales minus Purchases Card:** Real-time cash difference for today, this month, and all time.
- **Sales & Purchases Cards:** Total revenue and expense totals with transaction counts.
- **Rule-Based Stock Alerts:** Red warning banners for any ingredient where `Current Stock <= Minimum Threshold`.
- **Smart Shortage Predictor (ML-Ready):** Transparently indicates `"Not enough data yet (X/30 days recorded)"`. Shows progress towards enough real time-series history to train predictive models.
- **Recent Activity Feed:** Instant timeline of latest sales, purchases, and baking deductions.

### 2. 🍰 Sales
- **Record Sale:** Cake name (autocomplete from saved recipes), quantity stepper, total amount (₹), sale date (defaults to today), customer name, payment method chips (Cash, UPI/GPay, Card, Other), and custom notes.
- **Daily & Monthly Totals:** Automatic breakdown at the top of the screen.
- **Filter & Search:** Filter by Today, This Week, This Month, or search by customer / cake flavor.

### 3. 🧾 Purchases
- **Record Bill:** Total bill amount (₹), purchase date, and store/supplier name.
- **Itemized Ingredient Option:** Add line items (e.g. Butter 1000g @ ₹550).
- **Auto-Restock Checkbox:** Check *"Automatically add line items to inventory stock"* to credit inventory and log restock in a single step!

### 4. 📦 Inventory (Stock)
- **Track Ingredients:** Current quantity, unit (`g`, `kg`, `ml`, `L`, `pcs`, `tsp`, `tbsp`), category, and minimum stock threshold.
- **Stock Warnings:** Visual badges for items requiring restock.
- **Adjust Stock:** Fast "+ Restock", "- Waste", or "Correction" with reason logging and real-time balance preview.
- **Audit Logs:** View the complete dated history of every addition, bake deduction, and adjustment.

### 5. 📖 Recipes & Baking Workflow
- **Saved Recipes:** Yield description, category, and list of required ingredients.
- **🎂 Bake a Cake:**
  1. Mom taps **"🎂 Bake Cake"** on any recipe card.
  2. Multiplier stepper allows 0.5x, 1x, 2x, etc.
  3. The app previews exact required quantities vs available inventory stock.
  4. Shortages or low-stock alerts are highlighted in red/amber.
  5. Mom must tap **"✅ Confirm & Deduct Stock"** before ingredients are deducted.
  6. The app asks if she'd like to immediately record the freshly baked cake as a sale!

### 6. 🛒 Shopping List
- **⚡ Auto-Add Low Stock Items:** 1-tap scan of inventory that automatically adds all low-stock items with recommended restock amounts.
- **Manual Add:** Add cake boxes, golden ribbons, essence, etc.
- **Check Off / Mark Bought:**
  - Automatically updates the inventory stock balance.
  - Optional checkbox to also record it as a Purchase Expense.
- **Clear Done:** Cleans up completed shopping items.

### 7. 📥 CSV Exports
Download official business records anytime:
- `sales_records_<date>.csv`
- `purchase_records_<date>.csv`
- `inventory_status_<date>.csv`
- `stock_history_logs_<date>.csv`

---

## 🔒 Owner Security
- Password can be changed anytime by tapping the profile icon 👤 in the header.
- Token is stored locally on the phone. Logging out immediately invalidates client sessions.

---

## 🧪 Testing
To run the automated verification test suite:
```bash
python test_suite.py
```
This tests all 7 modules end-to-end: authentication, sales, purchases, inventory, recipes/baking deductions, shopping list restocks, dashboard metrics, and CSV exports.
