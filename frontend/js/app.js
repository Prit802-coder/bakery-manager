import { api, authStorage } from "./api.js";

// State
let currentView = "dashboard";
let allIngredients = [];
let allRecipes = [];
let activeBakeRecipeId = null;

// ==========================================
// TOAST NOTIFICATIONS
// ==========================================
export function showToast(message, type = "success") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <span>${message}</span>
    <span style="cursor: pointer; margin-left: 12px; font-size: 16px;">&times;</span>
  `;

  toast.querySelector("span:last-child").onclick = () => toast.remove();

  container.appendChild(toast);
  setTimeout(() => {
    if (toast.parentElement) toast.remove();
  }, 4000);
}

// ==========================================
// MODAL MANAGEMENT
// ==========================================
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add("open");
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove("open");
  }
}

function initModalClosers() {
  document.querySelectorAll("[data-close-modal]").forEach(btn => {
    btn.addEventListener("click", () => {
      const modal = btn.closest(".modal-overlay");
      if (modal) modal.classList.remove("open");
    });
  });

  // Close when clicking on overlay background
  document.querySelectorAll(".modal-overlay").forEach(overlay => {
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) {
        overlay.classList.remove("open");
      }
    });
  });
}

// ==========================================
// NAVIGATION & VIEW SWITCHING
// ==========================================
function switchView(viewName) {
  currentView = viewName;

  // Update nav items
  document.querySelectorAll(".nav-item").forEach(item => {
    if (item.dataset.nav === viewName) {
      item.classList.add("active");
    } else {
      item.classList.remove("active");
    }
  });

  // Update views
  document.querySelectorAll(".view-section").forEach(sec => {
    if (sec.id === `view-${viewName}`) {
      sec.classList.add("active");
    } else {
      sec.classList.remove("active");
    }
  });

  // Scroll to top
  window.scrollTo({ top: 0, behavior: "smooth" });

  // Load specific view data
  if (viewName === "dashboard") loadDashboard();
  else if (viewName === "sales") loadSales();
  else if (viewName === "purchases") loadPurchases();
  else if (viewName === "inventory") loadInventory();
  else if (viewName === "recipes") loadRecipes();
  else if (viewName === "shopping") loadShoppingList();
  else if (viewName === "exports") setupExportLinks();
}

function initNavigation() {
  document.querySelectorAll(".nav-item").forEach(item => {
    item.addEventListener("click", () => {
      switchView(item.dataset.nav);
    });
  });

  // Header quick buttons
  document.getElementById("btn-export-quick").addEventListener("click", () => {
    switchView("exports");
  });

  document.getElementById("btn-user-settings").addEventListener("click", () => {
    openModal("modal-user-settings");
    loadProfileModal();
  });

  document.getElementById("btn-logout").addEventListener("click", () => {
    if (confirm("Are you sure you want to log out?")) {
      api.logout();
    }
  });

  document.getElementById("btn-refresh-dashboard").addEventListener("click", () => {
    loadDashboard();
    showToast("Dashboard refreshed", "success");
  });

  // Dashboard quick actions
  document.getElementById("action-quick-sale").addEventListener("click", () => {
    openNewSaleModal();
  });

  document.getElementById("action-quick-bake").addEventListener("click", () => {
    switchView("recipes");
  });

  document.getElementById("action-quick-purchase").addEventListener("click", () => {
    openNewPurchaseModal();
  });

  document.getElementById("action-quick-shopping").addEventListener("click", () => {
    switchView("shopping");
  });

  document.getElementById("btn-dash-auto-shopping").addEventListener("click", async () => {
    await autoAddLowStock();
  });
}

// ==========================================
// AUTHENTICATION & LOGIN SCREEN
// ==========================================
function checkAuth() {
  const isAuth = authStorage.isAuthenticated();
  const loginScreen = document.getElementById("login-screen");
  const appContainer = document.getElementById("app-container");

  if (isAuth) {
    loginScreen.style.display = "none";
    appContainer.style.display = "block";
    loadDashboard();
    preloadCommonData();
  } else {
    loginScreen.style.display = "flex";
    appContainer.style.display = "none";
  }
}

function initAuthHandlers() {
  const loginForm = document.getElementById("login-form");
  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const username = document.getElementById("login-username").value.trim();
    const password = document.getElementById("login-password").value;
    const btn = document.getElementById("login-btn");

    try {
      btn.disabled = true;
      btn.innerText = "Signing in...";
      await api.login(username, password);
      showToast("Welcome back, Baker Mom!", "success");
      checkAuth();
    } catch (err) {
      showToast(err.message || "Login failed", "error");
    } finally {
      btn.disabled = false;
      btn.innerText = "Log In to Bakery";
    }
  });

  window.addEventListener("auth:unauthorized", () => {
    showToast("Session expired. Please log in again.", "warning");
    checkAuth();
  });

  window.addEventListener("auth:logged_out", () => {
    showToast("Logged out successfully.", "success");
    checkAuth();
  });

  // Password change
  const pwdForm = document.getElementById("form-change-password");
  pwdForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const cur = document.getElementById("pwd-current").value;
    const nw = document.getElementById("pwd-new").value;
    try {
      await api.changePassword(cur, nw);
      showToast("Password updated successfully!", "success");
      pwdForm.reset();
      closeModal("modal-user-settings");
    } catch (err) {
      showToast(err.message, "error");
    }
  });
}

async function loadProfileModal() {
  const user = authStorage.getUser();
  if (user) {
    document.getElementById("profile-full-name").innerText = user.full_name || "Bakery Owner";
    document.getElementById("profile-username").innerText = `Username: ${user.username}`;
  }
}

async function preloadCommonData() {
  try {
    allIngredients = await api.getIngredients();
    allRecipes = await api.getRecipes();
    updateCakeSuggestions();
  } catch (err) {
    console.error("Error preloading data:", err);
  }
}

function updateCakeSuggestions() {
  const datalist = document.getElementById("cake-suggestions");
  if (!datalist) return;
  datalist.innerHTML = "";
  allRecipes.forEach(r => {
    const opt = document.createElement("option");
    opt.value = r.name;
    datalist.appendChild(opt);
  });
}

// ==========================================
// 1. DASHBOARD LOGIC
// ==========================================
async function loadDashboard() {
  try {
    const metrics = await api.getDashboardMetrics();

    // Sales
    document.getElementById("dash-sales-month").innerText = `₹${metrics.sales_month.toFixed(2)}`;
    document.getElementById("dash-sales-sub").innerText = `Today: ₹${metrics.sales_today.toFixed(2)} (${metrics.sales_count_month} orders this mo)`;

    // Purchases
    document.getElementById("dash-purchases-month").innerText = `₹${metrics.purchases_month.toFixed(2)}`;
    document.getElementById("dash-purchases-sub").innerText = `Today: ₹${metrics.purchases_today.toFixed(2)} (${metrics.purchases_count_month} bills this mo)`;

    // Net: Sales minus Purchases (explicitly NOT labeled profit!)
    const netMonth = metrics.sales_minus_purchases_month;
    const netEl = document.getElementById("dash-net-month");
    netEl.innerText = `${netMonth >= 0 ? "+" : ""}₹${netMonth.toFixed(2)}`;
    netEl.className = `net-value-large ${netMonth >= 0 ? "net-positive" : "net-negative"}`;

    const netToday = metrics.sales_minus_purchases_today;
    const netAllTime = metrics.sales_minus_purchases_all_time;
    document.getElementById("dash-net-sub").innerText =
      `Today: ${netToday >= 0 ? "+" : ""}₹${netToday.toFixed(2)} | All-time: ${netAllTime >= 0 ? "+" : ""}₹${netAllTime.toFixed(2)}`;

    // Stock Warnings
    const stockAlertCard = document.getElementById("dash-stock-alerts-card");
    const stockAlertList = document.getElementById("dash-stock-alerts-list");
    const stockBadge = document.getElementById("nav-badge-stock");

    document.getElementById("dash-low-stock-count").innerText = metrics.low_stock_count;

    if (metrics.low_stock_count > 0) {
      stockBadge.style.display = "flex";
      stockBadge.innerText = metrics.low_stock_count;
      stockAlertCard.style.display = "block";

      stockAlertList.innerHTML = metrics.stock_alerts.map(item => `
        <div class="alert-item">
          <div>
            <div class="alert-name">${item.name}</div>
            <div class="alert-deficit">
              Current: ${item.quantity} ${item.unit} (Min: ${item.min_stock} ${item.unit})
            </div>
          </div>
          <button class="btn btn-primary btn-sm btn-quick-restock" data-ing-id="${item.id}" data-name="${item.name}" data-unit="${item.unit}" data-qty="${item.quantity}">
            Restock
          </button>
        </div>
      `).join("");

      stockAlertList.querySelectorAll(".btn-quick-restock").forEach(btn => {
        btn.addEventListener("click", () => {
          openAdjustStockModal(
            parseInt(btn.dataset.ingId),
            btn.dataset.name,
            parseFloat(btn.dataset.qty),
            btn.dataset.unit
          );
        });
      });
    } else {
      stockBadge.style.display = "none";
      stockAlertCard.style.display = "none";
    }

    // Machine Learning Shortage Predictor Card
    const ml = metrics.shortage_predictor;
    const mlPill = document.getElementById("ml-status-pill");
    const mlBar = document.getElementById("ml-progress-fill");
    const mlText = document.getElementById("ml-status-text");

    mlPill.innerText = ml.status_label;
    const pct = Math.min(100, Math.round((ml.days_recorded / ml.minimum_days_required) * 100));
    mlBar.style.width = `${pct}%`;
    mlText.innerText = ml.explanation;

    // Recent Activity Feed
    renderRecentActivity(metrics.recent_sales, metrics.recent_purchases, metrics.recent_bakes);

    // Refresh shopping badge count
    const shoppingItems = await api.getShoppingList(false);
    const shopBadge = document.getElementById("nav-badge-shopping");
    if (shoppingItems.length > 0) {
      shopBadge.style.display = "flex";
      shopBadge.innerText = shoppingItems.length;
      document.getElementById("dash-shopping-sub").innerText = `${shoppingItems.length} items needed`;
    } else {
      shopBadge.style.display = "none";
      document.getElementById("dash-shopping-sub").innerText = "All stocked";
    }

  } catch (err) {
    console.error("Dashboard load failed:", err);
  }
}

function renderRecentActivity(sales, purchases, bakes) {
  const container = document.getElementById("dash-recent-activity");
  const activities = [];

  sales.forEach(s => activities.push({
    type: "sale",
    title: `Sold: ${s.quantity}x ${s.cake_type}`,
    sub: `${s.date} • ${s.payment_method} • ${s.customer_name || "In-person"}`,
    amount: `+₹${s.amount.toFixed(2)}`,
    isPositive: true,
    rawDate: new Date(s.created_at || s.date)
  }));

  purchases.forEach(p => activities.push({
    type: "purchase",
    title: `Purchase: ${p.supplier || "Bakery Supplies"}`,
    sub: `${p.date} • Bill #${p.id}`,
    amount: `-₹${p.bill_total.toFixed(2)}`,
    isPositive: false,
    rawDate: new Date(p.created_at || p.date)
  }));

  bakes.forEach(b => activities.push({
    type: "bake",
    title: `Baked: ${b.multiplier}x ${b.recipe_name}`,
    sub: `${b.date} • Stock deducted`,
    amount: "🎂",
    isPositive: null,
    rawDate: new Date(b.created_at || b.date)
  }));

  activities.sort((a, b) => b.rawDate - a.rawDate);

  if (activities.length === 0) {
    container.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 12px; font-size: 13px;">No recent activity yet.</div>`;
    return;
  }

  container.innerHTML = activities.slice(0, 6).map(act => `
    <div style="display: flex; align-items: center; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid var(--border-light);">
      <div style="display: flex; align-items: center; gap: 10px;">
        <span style="font-size: 18px;">${act.type === "sale" ? "🍰" : (act.type === "purchase" ? "🧾" : "🎂")}</span>
        <div>
          <div style="font-size: 13px; font-weight: 700; color: var(--text-main);">${act.title}</div>
          <div style="font-size: 11px; color: var(--text-muted);">${act.sub}</div>
        </div>
      </div>
      <div style="font-weight: 800; font-size: 14px; color: ${act.isPositive === true ? "var(--success)" : (act.isPositive === false ? "var(--danger)" : "var(--primary)")};">
        ${act.amount}
      </div>
    </div>
  `).join("");
}

// ==========================================
// 2. SALES LOGIC
// ==========================================
let currentSalesFilter = "all";

async function loadSales() {
  try {
    const summary = await api.getSalesSummary();
    document.getElementById("sales-today-val").innerText = `₹${summary.today_total.toFixed(2)}`;
    document.getElementById("sales-today-count").innerText = `${summary.today_count} sale(s)`;
    document.getElementById("sales-month-val").innerText = `₹${summary.this_month_total.toFixed(2)}`;
    document.getElementById("sales-month-count").innerText = `${summary.this_month_count} sale(s)`;

    fetchFilteredSales();
  } catch (err) {
    console.error("Sales load failed:", err);
  }
}

async function fetchFilteredSales() {
  const container = document.getElementById("sales-list-container");
  const search = document.getElementById("sales-search-input").value.trim();

  const params = {};
  if (search) params.cake_type = search;

  const todayStr = new Date().toISOString().split("T")[0];
  if (currentSalesFilter === "today") {
    params.start_date = todayStr;
    params.end_date = todayStr;
  } else if (currentSalesFilter === "week") {
    const d = new Date();
    d.setDate(d.getDate() - 7);
    params.start_date = d.toISOString().split("T")[0];
  } else if (currentSalesFilter === "month") {
    const d = new Date();
    d.setDate(1);
    params.start_date = d.toISOString().split("T")[0];
  }

  const sales = await api.getSales(params);

  if (sales.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">🍰</div>
        <div class="empty-state-title">No Sales Found</div>
        <div class="empty-state-desc">Record your in-person cake sales to track your revenue.</div>
        <button id="btn-empty-sale" class="btn btn-primary btn-sm">➕ Record a Sale</button>
      </div>
    `;
    const btn = document.getElementById("btn-empty-sale");
    if (btn) btn.onclick = openNewSaleModal;
    return;
  }

  container.innerHTML = sales.map(s => `
    <div class="item-card">
      <div class="item-card-header">
        <div>
          <div class="item-card-title">${s.cake_type}</div>
          <div class="item-card-meta">
            ${s.date} • Quantity: <strong>${s.quantity}</strong> • ${s.customer_name ? `Customer: ${s.customer_name}` : "Walk-in"}
          </div>
        </div>
        <div class="item-card-price">₹${s.amount.toFixed(2)}</div>
      </div>
      ${s.notes ? `<div style="font-size: 12px; color: var(--text-muted); background: var(--bg-app); padding: 4px 8px; border-radius: 4px; margin: 6px 0;">📝 ${s.notes}</div>` : ""}
      <div class="item-card-footer">
        <span class="badge badge-neutral">💳 ${s.payment_method || "Cash"}</span>
        <button class="btn btn-danger btn-sm btn-delete-sale" data-sale-id="${s.id}">
          🗑️ Delete
        </button>
      </div>
    </div>
  `).join("");

  container.querySelectorAll(".btn-delete-sale").forEach(btn => {
    btn.onclick = async () => {
      if (confirm("Delete this sale record?")) {
        await api.deleteSale(btn.dataset.saleId);
        showToast("Sale record deleted", "success");
        loadSales();
        loadDashboard();
      }
    };
  });
}

function openNewSaleModal(prefillCake = "") {
  document.getElementById("form-sale").reset();
  document.getElementById("sale-edit-id").value = "";
  document.getElementById("sale-date").value = new Date().toISOString().split("T")[0];
  document.getElementById("sale-quantity").value = "1";
  document.getElementById("sale-payment-method").value = "Cash";

  // Reset payment chips
  document.querySelectorAll("#sale-payment-chips .chip-btn").forEach(c => {
    c.classList.toggle("active", c.dataset.payment === "Cash");
  });

  if (prefillCake) {
    document.getElementById("sale-cake-type").value = prefillCake;
  }

  openModal("modal-sale");
}

function initSalesEvents() {
  document.getElementById("btn-open-new-sale").onclick = () => openNewSaleModal();

  // Filter pills
  document.querySelectorAll("[data-sales-filter]").forEach(pill => {
    pill.onclick = () => {
      document.querySelectorAll("[data-sales-filter]").forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      currentSalesFilter = pill.dataset.salesFilter;
      fetchFilteredSales();
    };
  });

  document.getElementById("sales-search-input").oninput = () => {
    fetchFilteredSales();
  };

  // Quantity Stepper
  document.getElementById("btn-sale-qty-minus").onclick = () => {
    const input = document.getElementById("sale-quantity");
    const val = parseFloat(input.value) || 1;
    if (val > 0.5) input.value = (val - 0.5).toString();
  };

  document.getElementById("btn-sale-qty-plus").onclick = () => {
    const input = document.getElementById("sale-quantity");
    const val = parseFloat(input.value) || 1;
    input.value = (val + 0.5).toString();
  };

  // Payment Chips
  document.querySelectorAll("#sale-payment-chips .chip-btn").forEach(chip => {
    chip.onclick = () => {
      document.querySelectorAll("#sale-payment-chips .chip-btn").forEach(c => c.classList.remove("active"));
      chip.classList.add("active");
      document.getElementById("sale-payment-method").value = chip.dataset.payment;
    };
  });

  // Form Submit
  document.getElementById("form-sale").onsubmit = async (e) => {
    e.preventDefault();
    const saleData = {
      cake_type: document.getElementById("sale-cake-type").value.trim(),
      quantity: parseFloat(document.getElementById("sale-quantity").value) || 1,
      amount: parseFloat(document.getElementById("sale-amount").value),
      date: document.getElementById("sale-date").value,
      customer_name: document.getElementById("sale-customer").value.trim() || null,
      payment_method: document.getElementById("sale-payment-method").value,
      notes: document.getElementById("sale-notes").value.trim() || null
    };

    try {
      await api.createSale(saleData);
      showToast(`Sale of ₹${saleData.amount} recorded!`, "success");
      closeModal("modal-sale");
      loadSales();
      loadDashboard();
    } catch (err) {
      showToast(err.message, "error");
    }
  };
}

// ==========================================
// 3. PURCHASES LOGIC
// ==========================================
let currentPurchasesFilter = "all";

async function loadPurchases() {
  try {
    const summary = await api.getPurchasesSummary();
    document.getElementById("purchases-today-val").innerText = `₹${summary.today_total.toFixed(2)}`;
    document.getElementById("purchases-today-count").innerText = `${summary.today_count} bill(s)`;
    document.getElementById("purchases-month-val").innerText = `₹${summary.this_month_total.toFixed(2)}`;
    document.getElementById("purchases-month-count").innerText = `${summary.this_month_count} bill(s)`;

    fetchFilteredPurchases();
  } catch (err) {
    console.error("Purchases load failed:", err);
  }
}

async function fetchFilteredPurchases() {
  const container = document.getElementById("purchases-list-container");
  const params = {};
  const todayStr = new Date().toISOString().split("T")[0];

  if (currentPurchasesFilter === "today") {
    params.start_date = todayStr;
    params.end_date = todayStr;
  } else if (currentPurchasesFilter === "month") {
    const d = new Date();
    d.setDate(1);
    params.start_date = d.toISOString().split("T")[0];
  }

  const purchases = await api.getPurchases(params);

  if (purchases.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">🧾</div>
        <div class="empty-state-title">No Purchases Logged</div>
        <div class="empty-state-desc">Record grocery and ingredient receipts to track business expenses.</div>
        <button id="btn-empty-purchase" class="btn btn-primary btn-sm">➕ Add a Purchase Bill</button>
      </div>
    `;
    const btn = document.getElementById("btn-empty-purchase");
    if (btn) btn.onclick = openNewPurchaseModal;
    return;
  }

  container.innerHTML = purchases.map(p => `
    <div class="item-card">
      <div class="item-card-header">
        <div>
          <div class="item-card-title">${p.supplier || "Bakery Supplies"}</div>
          <div class="item-card-meta">${p.date} • Bill #${p.id}</div>
        </div>
        <div class="item-card-price" style="color: var(--secondary);">₹${p.bill_total.toFixed(2)}</div>
      </div>

      ${p.items && p.items.length > 0 ? `
        <div style="background-color: var(--bg-app); border-radius: 6px; padding: 8px 10px; margin: 8px 0; font-size: 12px;">
          <div style="font-weight: 700; margin-bottom: 4px; color: var(--text-muted);">Items Bought:</div>
          ${p.items.map(it => `
            <div style="display: flex; justify-content: space-between;">
              <span>• ${it.item_name} (${it.quantity} ${it.unit})</span>
              <span>₹${it.cost.toFixed(2)}</span>
            </div>
          `).join("")}
        </div>
      ` : ""}

      ${p.notes ? `<div style="font-size: 12px; color: var(--text-muted); margin-bottom: 6px;">📝 ${p.notes}</div>` : ""}

      <div class="item-card-footer">
        <span style="font-size: 11px; color: var(--text-muted);">Expense Record</span>
        <button class="btn btn-danger btn-sm btn-delete-purchase" data-purchase-id="${p.id}">
          🗑️ Delete
        </button>
      </div>
    </div>
  `).join("");

  container.querySelectorAll(".btn-delete-purchase").forEach(btn => {
    btn.onclick = async () => {
      if (confirm("Delete this purchase record?")) {
        await api.deletePurchase(btn.dataset.purchaseId);
        showToast("Purchase record deleted", "success");
        loadPurchases();
        loadDashboard();
      }
    };
  });
}

function openNewPurchaseModal() {
  document.getElementById("form-purchase").reset();
  document.getElementById("purchase-date").value = new Date().toISOString().split("T")[0];
  document.getElementById("purchase-items-container").innerHTML = "";
  document.getElementById("purchase-update-stock").checked = false;
  openModal("modal-purchase");
}

function addPurchaseItemRow() {
  const container = document.getElementById("purchase-items-container");
  const rowId = `pi-row-${Date.now()}`;
  const row = document.createElement("div");
  row.id = rowId;
  row.style.display = "grid";
  row.style.gridTemplateColumns = "2fr 1fr 1fr auto";
  row.style.gap = "6px";
  row.style.alignItems = "center";

  row.innerHTML = `
    <input type="text" class="form-control pi-name" placeholder="Item name" required style="font-size: 13px; min-height: 38px;">
    <input type="number" class="form-control pi-qty" placeholder="Qty" value="1" min="0.1" step="any" required style="font-size: 13px; min-height: 38px;">
    <input type="number" class="form-control pi-cost" placeholder="₹" min="0" step="any" style="font-size: 13px; min-height: 38px;">
    <button type="button" class="btn btn-danger btn-sm" style="min-height: 38px; padding: 0 10px;">&times;</button>
  `;

  row.querySelector("button").onclick = () => row.remove();
  container.appendChild(row);
}

function initPurchasesEvents() {
  document.getElementById("btn-open-new-purchase").onclick = () => openNewPurchaseModal();

  document.getElementById("btn-add-purchase-item").onclick = () => addPurchaseItemRow();

  document.querySelectorAll("[data-purchases-filter]").forEach(pill => {
    pill.onclick = () => {
      document.querySelectorAll("[data-purchases-filter]").forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      currentPurchasesFilter = pill.dataset.purchasesFilter;
      fetchFilteredPurchases();
    };
  });

  document.getElementById("form-purchase").onsubmit = async (e) => {
    e.preventDefault();

    const items = [];
    document.querySelectorAll("#purchase-items-container > div").forEach(r => {
      const name = r.querySelector(".pi-name").value.trim();
      const qty = parseFloat(r.querySelector(".pi-qty").value) || 1;
      const cost = parseFloat(r.querySelector(".pi-cost").value) || 0;
      if (name) {
        items.push({
          item_name: name,
          quantity: qty,
          unit: "pcs",
          cost: cost
        });
      }
    });

    const purchaseData = {
      bill_total: parseFloat(document.getElementById("purchase-bill-total").value),
      date: document.getElementById("purchase-date").value,
      supplier: document.getElementById("purchase-supplier").value.trim() || null,
      notes: document.getElementById("purchase-notes").value.trim() || null,
      update_inventory_stock: document.getElementById("purchase-update-stock").checked,
      items: items.length > 0 ? items : null
    };

    try {
      await api.createPurchase(purchaseData);
      showToast(`Purchase bill of ₹${purchaseData.bill_total} recorded!`, "success");
      closeModal("modal-purchase");
      loadPurchases();
      loadDashboard();
      preloadCommonData();
    } catch (err) {
      showToast(err.message, "error");
    }
  };
}

// ==========================================
// 4. INVENTORY LOGIC
// ==========================================
let currentStockFilter = "all";

async function loadInventory() {
  try {
    allIngredients = await api.getIngredients();
    renderFilteredInventory();
  } catch (err) {
    console.error("Inventory load failed:", err);
  }
}

function renderFilteredInventory() {
  const container = document.getElementById("inventory-list-container");
  const search = document.getElementById("inventory-search-input").value.trim().toLowerCase();

  let filtered = allIngredients.filter(ing => {
    if (search && !ing.name.toLowerCase().includes(search)) return false;

    if (currentStockFilter === "low") {
      return ing.is_low_stock;
    } else if (currentStockFilter === "flour") {
      return ing.category.toLowerCase().includes("flour") || ing.category.toLowerCase().includes("dry");
    } else if (currentStockFilter === "dairy") {
      return ing.category.toLowerCase().includes("dairy") || ing.category.toLowerCase().includes("egg");
    } else if (currentStockFilter === "packaging") {
      return ing.category.toLowerCase().includes("pack");
    }
    return true;
  });

  if (filtered.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">📦</div>
        <div class="empty-state-title">No Ingredients Found</div>
        <div class="empty-state-desc">Add raw ingredients, packaging, or flavorings to track your stock.</div>
        <button id="btn-empty-ingredient" class="btn btn-primary btn-sm">➕ Add Ingredient</button>
      </div>
    `;
    const btn = document.getElementById("btn-empty-ingredient");
    if (btn) btn.onclick = openNewIngredientModal;
    return;
  }

  container.innerHTML = filtered.map(ing => `
    <div class="item-card" style="${ing.is_low_stock ? "border-left: 4px solid var(--danger);" : ""}">
      <div class="item-card-header">
        <div>
          <div class="item-card-title">${ing.name}</div>
          <div class="item-card-meta">Category: ${ing.category}</div>
        </div>
        <div style="text-align: right;">
          <div style="font-size: 19px; font-weight: 800; color: ${ing.is_low_stock ? "var(--danger)" : "var(--primary)"};">
            ${ing.quantity} ${ing.unit}
          </div>
          <div style="font-size: 11px; color: var(--text-muted);">Min: ${ing.min_stock} ${ing.unit}</div>
        </div>
      </div>

      <div style="display: flex; align-items: center; justify-content: space-between; margin-top: 10px; padding-top: 8px; border-top: 1px solid var(--border-light);">
        <div>
          ${ing.is_low_stock
            ? `<span class="badge badge-danger">⚠️ LOW STOCK ALERT</span>`
            : `<span class="badge badge-success">✓ In Stock</span>`}
        </div>

        <div style="display: flex; gap: 6px;">
          <button class="btn btn-primary btn-sm btn-adjust-stock" data-ing-id="${ing.id}" data-name="${ing.name}" data-qty="${ing.quantity}" data-unit="${ing.unit}">
            ⚡ Adjust
          </button>
          <button class="btn btn-secondary btn-sm btn-edit-ing" data-ing-id="${ing.id}">
            ✏️
          </button>
          <button class="btn btn-danger btn-sm btn-delete-ing" data-ing-id="${ing.id}" data-name="${ing.name}">
            🗑️
          </button>
        </div>
      </div>
    </div>
  `).join("");

  container.querySelectorAll(".btn-adjust-stock").forEach(btn => {
    btn.onclick = () => {
      openAdjustStockModal(
        parseInt(btn.dataset.ingId),
        btn.dataset.name,
        parseFloat(btn.dataset.qty),
        btn.dataset.unit
      );
    };
  });

  container.querySelectorAll(".btn-edit-ing").forEach(btn => {
    btn.onclick = () => {
      const ing = allIngredients.find(i => i.id === parseInt(btn.dataset.ingId));
      if (ing) openEditIngredientModal(ing);
    };
  });

  container.querySelectorAll(".btn-delete-ing").forEach(btn => {
    btn.onclick = async () => {
      if (confirm(`Delete ingredient '${btn.dataset.name}'?`)) {
        await api.deleteIngredient(btn.dataset.ingId);
        showToast("Ingredient deleted", "success");
        loadInventory();
        loadDashboard();
      }
    };
  });
}

function openNewIngredientModal() {
  document.getElementById("form-ingredient").reset();
  document.getElementById("ingredient-edit-id").value = "";
  document.getElementById("modal-ingredient-title").innerText = "Add Ingredient";
  openModal("modal-ingredient");
}

function openEditIngredientModal(ing) {
  document.getElementById("ingredient-edit-id").value = ing.id;
  document.getElementById("modal-ingredient-title").innerText = "Edit Ingredient";
  document.getElementById("ingredient-name").value = ing.name;
  document.getElementById("ingredient-category").value = ing.category;
  document.getElementById("ingredient-unit").value = ing.unit;
  document.getElementById("ingredient-quantity").value = ing.quantity;
  document.getElementById("ingredient-min-stock").value = ing.min_stock;
  document.getElementById("ingredient-cost").value = ing.cost_per_unit || "";
  document.getElementById("ingredient-notes").value = ing.notes || "";
  openModal("modal-ingredient");
}

let activeAdjustIng = null;

function openAdjustStockModal(ingId, name, qty, unit) {
  activeAdjustIng = { id: ingId, name, qty, unit };
  document.getElementById("adjust-ingredient-id").value = ingId;
  document.getElementById("adjust-ingredient-name").innerText = name;
  document.getElementById("adjust-current-stock").innerText = `Current Stock: ${qty} ${unit}`;
  document.getElementById("adjust-delta").value = "";
  document.getElementById("adjust-reason").value = "";
  document.getElementById("adjust-preview-result").innerText = "";

  // Reset chips to restock
  document.querySelectorAll("#adjust-type-chips .chip-btn").forEach(c => {
    c.classList.toggle("active", c.dataset.type === "RESTOCK_PURCHASE");
  });
  document.getElementById("adjust-type").value = "RESTOCK_PURCHASE";

  openModal("modal-adjust-stock");
}

async function showInventoryLogsModal() {
  const container = document.getElementById("inventory-logs-list");
  container.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 20px;">Loading history...</div>`;
  openModal("modal-inventory-logs");

  try {
    const logs = await api.getInventoryLogs({ limit: 80 });
    if (logs.length === 0) {
      container.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 20px;">No change history recorded yet.</div>`;
      return;
    }

    container.innerHTML = logs.map(l => {
      const isPositive = l.quantity_delta > 0;
      return `
        <div style="background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: 8px; padding: 10px 12px;">
          <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div>
              <div style="font-weight: 700; font-size: 14px;">${l.ingredient_name}</div>
              <div style="font-size: 11px; color: var(--text-muted);">${new Date(l.created_at).toLocaleString()} • ${l.change_type}</div>
            </div>
            <div style="font-weight: 800; font-size: 15px; color: ${isPositive ? "var(--success)" : "var(--danger)"};">
              ${isPositive ? "+" : ""}${l.quantity_delta} ${l.unit}
            </div>
          </div>
          <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">
            Reason: <em>${l.reason || "Manual update"}</em> (Balance: ${l.quantity_after} ${l.unit})
          </div>
        </div>
      `;
    }).join("");
  } catch (err) {
    container.innerHTML = `<div style="color: var(--danger); text-align: center;">Failed to load logs: ${err.message}</div>`;
  }
}

function initInventoryEvents() {
  document.getElementById("btn-open-new-ingredient").onclick = () => openNewIngredientModal();

  document.getElementById("btn-toggle-inventory-logs").onclick = () => showInventoryLogsModal();

  document.querySelectorAll("[data-stock-filter]").forEach(pill => {
    pill.onclick = () => {
      document.querySelectorAll("[data-stock-filter]").forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      currentStockFilter = pill.dataset.stockFilter;
      renderFilteredInventory();
    };
  });

  document.getElementById("inventory-search-input").oninput = () => {
    renderFilteredInventory();
  };

  // Adjust stock chip selection
  document.querySelectorAll("#adjust-type-chips .chip-btn").forEach(chip => {
    chip.onclick = () => {
      document.querySelectorAll("#adjust-type-chips .chip-btn").forEach(c => c.classList.remove("active"));
      chip.classList.add("active");
      document.getElementById("adjust-type").value = chip.dataset.type;
    };
  });

  // Adjust live delta preview
  document.getElementById("adjust-delta").oninput = (e) => {
    if (!activeAdjustIng) return;
    const delta = parseFloat(e.target.value) || 0;
    const finalVal = activeAdjustIng.qty + delta;
    const previewEl = document.getElementById("adjust-preview-result");
    if (finalVal < 0) {
      previewEl.innerText = `⚠️ Result will be below zero: ${finalVal} ${activeAdjustIng.unit}`;
      previewEl.style.color = "var(--danger)";
    } else {
      previewEl.innerText = `Resulting Stock: ${finalVal} ${activeAdjustIng.unit}`;
      previewEl.style.color = "var(--primary)";
    }
  };

  // Adjust Form Submit
  document.getElementById("form-adjust-stock").onsubmit = async (e) => {
    e.preventDefault();
    const id = parseInt(document.getElementById("adjust-ingredient-id").value);
    const delta = parseFloat(document.getElementById("adjust-delta").value);
    const type = document.getElementById("adjust-type").value;
    const reason = document.getElementById("adjust-reason").value.trim();

    try {
      await api.adjustStock(id, {
        change_type: type,
        quantity_delta: delta,
        reason: reason
      });
      showToast("Stock updated successfully!", "success");
      closeModal("modal-adjust-stock");
      loadInventory();
      loadDashboard();
    } catch (err) {
      showToast(err.message, "error");
    }
  };

  // Ingredient Form Submit
  document.getElementById("form-ingredient").onsubmit = async (e) => {
    e.preventDefault();
    const editId = document.getElementById("ingredient-edit-id").value;
    const data = {
      name: document.getElementById("ingredient-name").value.trim(),
      category: document.getElementById("ingredient-category").value,
      unit: document.getElementById("ingredient-unit").value,
      quantity: parseFloat(document.getElementById("ingredient-quantity").value),
      min_stock: parseFloat(document.getElementById("ingredient-min-stock").value),
      cost_per_unit: parseFloat(document.getElementById("ingredient-cost").value) || 0,
      notes: document.getElementById("ingredient-notes").value.trim() || null
    };

    try {
      if (editId) {
        await api.updateIngredient(editId, data);
        showToast(`Ingredient '${data.name}' updated!`, "success");
      } else {
        await api.createIngredient(data);
        showToast(`Ingredient '${data.name}' added to inventory!`, "success");
      }
      closeModal("modal-ingredient");
      loadInventory();
      loadDashboard();
      preloadCommonData();
    } catch (err) {
      showToast(err.message, "error");
    }
  };
}

// ==========================================
// 5. RECIPES & "BAKE CAKE" LOGIC
// ==========================================
async function loadRecipes() {
  try {
    allRecipes = await api.getRecipes();
    renderFilteredRecipes();
  } catch (err) {
    console.error("Recipes load failed:", err);
  }
}

function renderFilteredRecipes() {
  const container = document.getElementById("recipes-list-container");
  const search = document.getElementById("recipes-search-input").value.trim().toLowerCase();

  const filtered = allRecipes.filter(r => {
    if (search && !r.name.toLowerCase().includes(search)) return false;
    return true;
  });

  if (filtered.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">📖</div>
        <div class="empty-state-title">No Recipes Saved</div>
        <div class="empty-state-desc">Save your cake recipes with ingredient amounts to enable one-tap baking deductions.</div>
        <button id="btn-empty-recipe" class="btn btn-primary btn-sm">➕ Create Recipe</button>
      </div>
    `;
    const btn = document.getElementById("btn-empty-recipe");
    if (btn) btn.onclick = openNewRecipeModal;
    return;
  }

  container.innerHTML = filtered.map(r => `
    <div class="item-card">
      <div class="item-card-header">
        <div>
          <div class="item-card-title">${r.name}</div>
          <div class="item-card-meta">Yield: ${r.yield_quantity} ${r.yield_unit} • ${r.category}</div>
        </div>
      </div>

      <!-- Ingredient list preview -->
      <div style="background-color: var(--bg-app); border-radius: 8px; padding: 10px 12px; margin: 10px 0; font-size: 13px;">
        <div style="font-weight: 700; color: var(--text-muted); margin-bottom: 6px;">Ingredients required:</div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 4px;">
          ${r.ingredients.map(ing => `
            <div>• ${ing.ingredient_name}: <strong>${ing.amount} ${ing.unit}</strong></div>
          `).join("")}
        </div>
      </div>

      ${r.instructions ? `<div style="font-size: 12px; color: var(--text-muted); margin-bottom: 8px;">👨‍🍳 ${r.instructions}</div>` : ""}

      <!-- Action buttons -->
      <div style="display: flex; gap: 8px; margin-top: 10px;">
        <button class="btn btn-primary btn-full btn-start-bake" data-recipe-id="${r.id}" data-name="${r.name}" style="background-color: #d97706;">
          🎂 Bake Cake
        </button>
        <button class="btn btn-danger btn-sm btn-delete-recipe" data-recipe-id="${r.id}" data-name="${r.name}">
          🗑️
        </button>
      </div>
    </div>
  `).join("");

  container.querySelectorAll(".btn-start-bake").forEach(btn => {
    btn.onclick = () => {
      openBakePreviewModal(parseInt(btn.dataset.recipeId), btn.dataset.name);
    };
  });

  container.querySelectorAll(".btn-delete-recipe").forEach(btn => {
    btn.onclick = async () => {
      if (confirm(`Delete recipe '${btn.dataset.name}'?`)) {
        await api.deleteRecipe(btn.dataset.recipeId);
        showToast("Recipe deleted", "success");
        loadRecipes();
      }
    };
  });
}

// BAKE CAKE CONFIRMATION WORKFLOW
async function openBakePreviewModal(recipeId, recipeName) {
  activeBakeRecipeId = recipeId;
  document.getElementById("bake-modal-title").innerText = `🎂 Bake: ${recipeName}`;
  document.getElementById("bake-multiplier").value = "1";
  openModal("modal-bake");
  await refreshBakePreview();
}

async function refreshBakePreview() {
  if (!activeBakeRecipeId) return;

  const multiplier = parseFloat(document.getElementById("bake-multiplier").value) || 1;
  const listContainer = document.getElementById("bake-ingredients-preview-list");
  const warningBox = document.getElementById("bake-warning-box");
  const confirmBtn = document.getElementById("btn-confirm-bake-action");

  listContainer.innerHTML = `<div style="text-align: center; color: var(--text-muted);">Calculating required stock...</div>`;
  warningBox.style.display = "none";

  try {
    const preview = await api.previewBake(activeBakeRecipeId, multiplier);
    document.getElementById("bake-yield-desc").innerText = `Yield for ${multiplier} batch: ${preview.yield_description}`;

    listContainer.innerHTML = preview.items.map(item => `
      <div class="confirm-item-row">
        <div>
          <span style="font-weight: 600;">${item.ingredient_name}</span>
          <span style="font-size: 11px; color: var(--text-muted); margin-left: 4px;">
            (In Stock: ${item.current_stock} ${item.stock_unit})
          </span>
        </div>
        <div style="text-align: right;">
          <strong style="color: ${item.is_sufficient ? "var(--text-main)" : "var(--danger)"};">
            -${item.required_amount} ${item.unit}
          </strong>
          <span style="font-size: 11px; margin-left: 6px;">
            ${item.is_sufficient ? "✓" : "❌ SHORT"}
          </span>
        </div>
      </div>
    `).join("");

    if (preview.warnings && preview.warnings.length > 0) {
      warningBox.style.display = "block";
      warningBox.innerHTML = `
        <div style="font-weight: 700; color: var(--warning); margin-bottom: 4px;">⚠️ Warnings:</div>
        ${preview.warnings.map(w => `<div style="font-size: 12px; margin-bottom: 2px;">• ${w}</div>`).join("")}
      `;
    }

    if (!preview.can_bake) {
      confirmBtn.disabled = true;
      confirmBtn.innerText = "❌ Insufficient Stock to Bake";
      confirmBtn.style.opacity = "0.5";
    } else {
      confirmBtn.disabled = false;
      confirmBtn.innerText = "✅ Confirm & Deduct Stock";
      confirmBtn.style.opacity = "1";
    }
  } catch (err) {
    listContainer.innerHTML = `<div style="color: var(--danger);">Error: ${err.message}</div>`;
  }
}

function openNewRecipeModal() {
  document.getElementById("form-recipe").reset();
  document.getElementById("recipe-edit-id").value = "";
  document.getElementById("recipe-ingredients-rows").innerHTML = "";

  // Add 3 starter ingredient rows
  addRecipeIngredientRow();
  addRecipeIngredientRow();
  addRecipeIngredientRow();

  openModal("modal-recipe");
}

function addRecipeIngredientRow(selectedIngId = null, amount = "", unit = "g") {
  const container = document.getElementById("recipe-ingredients-rows");
  const row = document.createElement("div");
  row.style.display = "grid";
  row.style.gridTemplateColumns = "2fr 1fr 1fr auto";
  row.style.gap = "6px";
  row.style.alignItems = "center";

  const ingOptions = allIngredients.map(ing => `
    <option value="${ing.id}" ${selectedIngId === ing.id ? "selected" : ""}>${ing.name} (${ing.unit})</option>
  `).join("");

  row.innerHTML = `
    <select class="form-control ri-ing-id" required style="font-size: 13px; min-height: 38px;">
      <option value="">Select ingredient...</option>
      ${ingOptions}
    </select>
    <input type="number" class="form-control ri-amount" placeholder="Amount" value="${amount}" min="0.1" step="any" required style="font-size: 13px; min-height: 38px;">
    <select class="form-control ri-unit" style="font-size: 13px; min-height: 38px;">
      <option value="g" ${unit === "g" ? "selected" : ""}>g</option>
      <option value="kg" ${unit === "kg" ? "selected" : ""}>kg</option>
      <option value="ml" ${unit === "ml" ? "selected" : ""}>ml</option>
      <option value="L" ${unit === "L" ? "selected" : ""}>L</option>
      <option value="pcs" ${unit === "pcs" ? "selected" : ""}>pcs</option>
      <option value="tsp" ${unit === "tsp" ? "selected" : ""}>tsp</option>
      <option value="tbsp" ${unit === "tbsp" ? "selected" : ""}>tbsp</option>
    </select>
    <button type="button" class="btn btn-danger btn-sm" style="min-height: 38px; padding: 0 10px;">&times;</button>
  `;

  row.querySelector("button").onclick = () => row.remove();
  container.appendChild(row);
}

function initRecipesEvents() {
  document.getElementById("btn-open-new-recipe").onclick = () => openNewRecipeModal();

  document.getElementById("btn-add-recipe-ingredient-row").onclick = () => addRecipeIngredientRow();

  document.getElementById("recipes-search-input").oninput = () => {
    renderFilteredRecipes();
  };

  // Multiplier Stepper for Bake
  document.getElementById("btn-bake-multiplier-minus").onclick = () => {
    const input = document.getElementById("bake-multiplier");
    const val = parseFloat(input.value) || 1;
    if (val > 0.5) {
      input.value = (val - 0.5).toString();
      refreshBakePreview();
    }
  };

  document.getElementById("btn-bake-multiplier-plus").onclick = () => {
    const input = document.getElementById("bake-multiplier");
    const val = parseFloat(input.value) || 1;
    input.value = (val + 0.5).toString();
    refreshBakePreview();
  };

  document.getElementById("bake-multiplier").onchange = () => {
    refreshBakePreview();
  };

  // CONFIRM BAKE SUBMISSION
  document.getElementById("btn-confirm-bake-action").onclick = async () => {
    if (!activeBakeRecipeId) return;
    const multiplier = parseFloat(document.getElementById("bake-multiplier").value) || 1;
    const btn = document.getElementById("btn-confirm-bake-action");

    try {
      btn.disabled = true;
      btn.innerText = "Deducting Ingredients...";
      const res = await api.confirmBake(activeBakeRecipeId, multiplier);
      closeModal("modal-bake");
      showToast(`🎂 Baked ${multiplier}x ${res.recipe_name}! Ingredients deducted.`, "success");

      // Update data
      loadDashboard();
      preloadCommonData();

      // Offer prompt to record as sale
      setTimeout(() => {
        if (confirm(`Would you like to record this freshly baked '${res.recipe_name}' as a sale now?`)) {
          switchView("sales");
          openNewSaleModal(res.recipe_name);
        }
      }, 500);

    } catch (err) {
      showToast(err.message, "error");
    } finally {
      btn.disabled = false;
      btn.innerText = "✅ Confirm & Deduct Stock";
    }
  };

  // Create Recipe Form Submit
  document.getElementById("form-recipe").onsubmit = async (e) => {
    e.preventDefault();
    const rows = document.querySelectorAll("#recipe-ingredients-rows > div");
    const ingredients = [];

    rows.forEach(r => {
      const ingId = parseInt(r.querySelector(".ri-ing-id").value);
      const amount = parseFloat(r.querySelector(".ri-amount").value);
      const unit = r.querySelector(".ri-unit").value;
      if (ingId && amount > 0) {
        ingredients.push({ ingredient_id: ingId, amount, unit });
      }
    });

    if (ingredients.length === 0) {
      showToast("Please add at least one ingredient to the recipe.", "warning");
      return;
    }

    const recipeData = {
      name: document.getElementById("recipe-name").value.trim(),
      category: document.getElementById("recipe-category").value,
      yield_quantity: 1.0,
      yield_unit: document.getElementById("recipe-yield-unit").value.trim(),
      instructions: document.getElementById("recipe-instructions").value.trim() || null,
      ingredients: ingredients
    };

    try {
      await api.createRecipe(recipeData);
      showToast(`Recipe '${recipeData.name}' created!`, "success");
      closeModal("modal-recipe");
      loadRecipes();
      preloadCommonData();
    } catch (err) {
      showToast(err.message, "error");
    }
  };
}

// ==========================================
// 6. SHOPPING LIST LOGIC
// ==========================================
let allShoppingItems = [];

async function loadShoppingList() {
  try {
    allShoppingItems = await api.getShoppingList(true);
    renderShoppingList();
  } catch (err) {
    console.error("Shopping list load failed:", err);
  }
}

function renderShoppingList() {
  const container = document.getElementById("shopping-list-container");

  if (allShoppingItems.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">🛒</div>
        <div class="empty-state-title">Shopping List is Clear</div>
        <div class="empty-state-desc">Tap 'Auto Add Low Stock' to automatically import low-stock ingredients, or add custom items.</div>
        <button id="btn-empty-auto-add" class="btn btn-primary btn-sm">⚡ Auto Add Low Stock Items</button>
      </div>
    `;
    const btn = document.getElementById("btn-empty-auto-add");
    if (btn) btn.onclick = autoAddLowStock;
    return;
  }

  container.innerHTML = allShoppingItems.map(item => `
    <div class="shopping-row ${item.is_bought ? "bought" : ""}">
      <div class="shopping-check btn-toggle-bought" data-item-id="${item.id}" data-is-bought="${item.is_bought}">
        ${item.is_bought ? "✓" : ""}
      </div>
      <div class="shopping-info">
        <div class="shopping-name">${item.name}</div>
        <div style="font-size: 12px; color: var(--text-muted);">
          <span class="shopping-qty">${item.quantity} ${item.unit}</span>
          ${item.notes ? `• ${item.notes}` : ""}
        </div>
      </div>
      <button class="btn btn-danger btn-sm btn-delete-shopping" data-item-id="${item.id}" style="padding: 4px 8px; min-height: 32px;">
        🗑️
      </button>
    </div>
  `).join("");

  container.querySelectorAll(".btn-toggle-bought").forEach(el => {
    el.onclick = () => {
      const id = parseInt(el.dataset.itemId);
      const isBought = el.dataset.isBought === "true";
      const item = allShoppingItems.find(i => i.id === id);

      if (!isBought && item) {
        // Open mark bought dialog to update stock & optionally expense
        openMarkBoughtModal(item);
      }
    };
  });

  container.querySelectorAll(".btn-delete-shopping").forEach(btn => {
    btn.onclick = async () => {
      await api.deleteShoppingItem(btn.dataset.itemId);
      showToast("Removed from shopping list", "success");
      loadShoppingList();
      loadDashboard();
    };
  });
}

async function autoAddLowStock() {
  try {
    const res = await api.autoAddLowStock();
    showToast(res.message, "success");
    loadShoppingList();
    loadDashboard();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function openMarkBoughtModal(item) {
  document.getElementById("mark-bought-item-id").value = item.id;
  document.getElementById("mark-bought-item-name").innerText = item.name;
  document.getElementById("mark-bought-item-qty").innerText = `Planned: ${item.quantity} ${item.unit}`;
  document.getElementById("mark-bought-actual-qty").value = item.quantity;
  document.getElementById("mark-bought-update-stock").checked = true;
  document.getElementById("mark-bought-record-expense").checked = false;
  document.getElementById("mark-bought-expense-wrap").style.display = "none";
  document.getElementById("mark-bought-cost").value = "";

  openModal("modal-mark-bought");
}

function initShoppingEvents() {
  document.getElementById("btn-shopping-auto-add").onclick = autoAddLowStock;

  document.getElementById("btn-open-new-shopping-item").onclick = () => {
    document.getElementById("form-shopping-item").reset();
    openModal("modal-shopping-item");
  };

  document.getElementById("btn-clear-bought-items").onclick = async () => {
    if (confirm("Clear all completed shopping items?")) {
      const res = await api.clearBoughtShoppingItems();
      showToast(res.message, "success");
      loadShoppingList();
    }
  };

  // Add Shopping Item Form
  document.getElementById("form-shopping-item").onsubmit = async (e) => {
    e.preventDefault();
    const data = {
      name: document.getElementById("shopping-item-name").value.trim(),
      quantity: parseFloat(document.getElementById("shopping-item-qty").value) || 1,
      unit: document.getElementById("shopping-item-unit").value.trim() || "pcs",
      notes: document.getElementById("shopping-item-notes").value.trim() || null
    };

    try {
      await api.addShoppingItem(data);
      showToast(`Added '${data.name}' to shopping list!`, "success");
      closeModal("modal-shopping-item");
      loadShoppingList();
      loadDashboard();
    } catch (err) {
      showToast(err.message, "error");
    }
  };

  // Toggle expense wrap inside mark bought
  document.getElementById("mark-bought-record-expense").onchange = (e) => {
    document.getElementById("mark-bought-expense-wrap").style.display = e.target.checked ? "block" : "none";
  };

  // Mark Bought Form Submit
  document.getElementById("form-mark-bought").onsubmit = async (e) => {
    e.preventDefault();
    const itemId = parseInt(document.getElementById("mark-bought-item-id").value);
    const actualQty = parseFloat(document.getElementById("mark-bought-actual-qty").value);
    const updateStock = document.getElementById("mark-bought-update-stock").checked;
    const recordExpense = document.getElementById("mark-bought-record-expense").checked;
    const cost = parseFloat(document.getElementById("mark-bought-cost").value) || null;

    try {
      const res = await api.markBought(itemId, updateStock, actualQty, recordExpense, cost);
      showToast(res.message, "success");
      closeModal("modal-mark-bought");
      loadShoppingList();
      loadDashboard();
      preloadCommonData();
    } catch (err) {
      showToast(err.message, "error");
    }
  };
}

// ==========================================
// 7. CSV EXPORTS
// ==========================================
function setupExportLinks() {
  document.getElementById("link-export-sales").href = api.getExportUrl("sales");
  document.getElementById("link-export-purchases").href = api.getExportUrl("purchases");
  document.getElementById("link-export-inventory").href = api.getExportUrl("inventory");
  document.getElementById("link-export-logs").href = api.getExportUrl("inventory-logs");
}

// ==========================================
// INITIALIZATION
// ==========================================
window.addEventListener("DOMContentLoaded", () => {
  initModalClosers();
  initNavigation();
  initAuthHandlers();
  initSalesEvents();
  initPurchasesEvents();
  initInventoryEvents();
  initRecipesEvents();
  initShoppingEvents();
  setupExportLinks();

  checkAuth();
});
