/**
 * API client module for Mom's Cake Business Manager
 */

const API_BASE = window.location.origin;

const TOKEN_KEY = "cake_app_token";
const USER_KEY = "cake_app_user";

export const authStorage = {
  getToken() {
    return localStorage.getItem(TOKEN_KEY);
  },
  setToken(token) {
    localStorage.setItem(TOKEN_KEY, token);
  },
  getUser() {
    try {
      const u = localStorage.getItem(USER_KEY);
      return u ? JSON.parse(u) : null;
    } catch {
      return null;
    }
  },
  setUser(user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },
  isAuthenticated() {
    return !!this.getToken();
  }
};

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const headers = options.headers || {};

  const token = authStorage.getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  if (options.body && typeof options.body === "object" && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(options.body);
  }

  options.headers = headers;

  try {
    const response = await fetch(url, options);

    if (response.status === 401) {
      // Unauthorized: clear token and notify auth state
      authStorage.clear();
      window.dispatchEvent(new CustomEvent("auth:unauthorized"));
      throw new Error("Your session has expired. Please log in again.");
    }

    if (!response.ok) {
      let errDetail = `Server error (${response.status})`;
      try {
        const errorJson = await response.json();
        if (errorJson.detail) {
          errDetail = Array.isArray(errorJson.detail)
            ? errorJson.detail.map(d => d.msg || JSON.stringify(d)).join(", ")
            : errorJson.detail;
        }
      } catch {
        // fallback
      }
      throw new Error(errDetail);
    }

    // Check if JSON response
    const contentType = response.headers.get("content-type");
    if (contentType && contentType.includes("application/json")) {
      return await response.json();
    }
    return response;
  } catch (err) {
    console.error(`API Error on ${endpoint}:`, err);
    throw err;
  }
}

export const api = {
  // Auth
  async login(username, password) {
    const data = await request("/api/auth/login", {
      method: "POST",
      body: { username, password }
    });
    authStorage.setToken(data.access_token);
    authStorage.setUser(data.user);
    return data;
  },
  async getMe() {
    return await request("/api/auth/me");
  },
  async changePassword(currentPassword, newPassword) {
    return await request("/api/auth/change-password", {
      method: "POST",
      body: { current_password: currentPassword, new_password: newPassword }
    });
  },
  logout() {
    authStorage.clear();
    window.dispatchEvent(new CustomEvent("auth:logged_out"));
  },

  // Dashboard
  async getDashboardMetrics() {
    return await request("/api/dashboard/metrics");
  },

  // Sales
  async getSales(params = {}) {
    const query = new URLSearchParams();
    if (params.start_date) query.append("start_date", params.start_date);
    if (params.end_date) query.append("end_date", params.end_date);
    if (params.cake_type) query.append("cake_type", params.cake_type);
    if (params.payment_method) query.append("payment_method", params.payment_method);
    const qs = query.toString() ? `?${query.toString()}` : "";
    return await request(`/api/sales${qs}`);
  },
  async getSalesSummary() {
    return await request("/api/sales/summary");
  },
  async createSale(saleData) {
    return await request("/api/sales", {
      method: "POST",
      body: saleData
    });
  },
  async updateSale(id, saleData) {
    return await request(`/api/sales/${id}`, {
      method: "PUT",
      body: saleData
    });
  },
  async deleteSale(id) {
    return await request(`/api/sales/${id}`, {
      method: "DELETE"
    });
  },

  // Purchases
  async getPurchases(params = {}) {
    const query = new URLSearchParams();
    if (params.start_date) query.append("start_date", params.start_date);
    if (params.end_date) query.append("end_date", params.end_date);
    if (params.supplier) query.append("supplier", params.supplier);
    const qs = query.toString() ? `?${query.toString()}` : "";
    return await request(`/api/purchases${qs}`);
  },
  async getPurchasesSummary() {
    return await request("/api/purchases/summary");
  },
  async createPurchase(purchaseData) {
    return await request("/api/purchases", {
      method: "POST",
      body: purchaseData
    });
  },
  async deletePurchase(id) {
    return await request(`/api/purchases/${id}`, {
      method: "DELETE"
    });
  },

  // Inventory
  async getIngredients(params = {}) {
    const query = new URLSearchParams();
    if (params.search) query.append("search", params.search);
    if (params.category) query.append("category", params.category);
    if (params.low_stock_only) query.append("low_stock_only", "true");
    const qs = query.toString() ? `?${query.toString()}` : "";
    return await request(`/api/inventory${qs}`);
  },
  async createIngredient(data) {
    return await request("/api/inventory", {
      method: "POST",
      body: data
    });
  },
  async updateIngredient(id, data) {
    return await request(`/api/inventory/${id}`, {
      method: "PUT",
      body: data
    });
  },
  async adjustStock(id, { change_type, quantity_delta, reason }) {
    return await request(`/api/inventory/${id}/adjust`, {
      method: "POST",
      body: { change_type, quantity_delta, reason }
    });
  },
  async deleteIngredient(id) {
    return await request(`/api/inventory/${id}`, {
      method: "DELETE"
    });
  },
  async getInventoryLogs(params = {}) {
    const query = new URLSearchParams();
    if (params.ingredient_id) query.append("ingredient_id", params.ingredient_id);
    if (params.change_type) query.append("change_type", params.change_type);
    const qs = query.toString() ? `?${query.toString()}` : "";
    return await request(`/api/inventory/logs${qs}`);
  },

  // Recipes & Baking
  async getRecipes(params = {}) {
    const query = new URLSearchParams();
    if (params.search) query.append("search", params.search);
    if (params.category) query.append("category", params.category);
    const qs = query.toString() ? `?${query.toString()}` : "";
    return await request(`/api/recipes${qs}`);
  },
  async createRecipe(data) {
    return await request("/api/recipes", {
      method: "POST",
      body: data
    });
  },
  async updateRecipe(id, data) {
    return await request(`/api/recipes/${id}`, {
      method: "PUT",
      body: data
    });
  },
  async deleteRecipe(id) {
    return await request(`/api/recipes/${id}`, {
      method: "DELETE"
    });
  },
  async previewBake(recipeId, multiplier = 1.0) {
    return await request(`/api/recipes/${recipeId}/bake-preview?multiplier=${multiplier}`);
  },
  async confirmBake(recipeId, multiplier = 1.0, notes = "") {
    return await request(`/api/recipes/${recipeId}/bake-confirm`, {
      method: "POST",
      body: { recipe_id: recipeId, multiplier, notes }
    });
  },

  // Shopping List
  async getShoppingList(includeBought = true) {
    return await request(`/api/shopping?include_bought=${includeBought}`);
  },
  async addShoppingItem(data) {
    return await request("/api/shopping", {
      method: "POST",
      body: data
    });
  },
  async autoAddLowStock() {
    return await request("/api/shopping/auto-add-low-stock", {
      method: "POST"
    });
  },
  async markBought(itemId, updateInventory = true, actualQty = null, recordPurchase = false, cost = null) {
    return await request(`/api/shopping/${itemId}/mark-bought`, {
      method: "POST",
      body: {
        update_inventory: updateInventory,
        actual_quantity: actualQty,
        record_purchase: recordPurchase,
        cost: cost
      }
    });
  },
  async deleteShoppingItem(id) {
    return await request(`/api/shopping/${id}`, {
      method: "DELETE"
    });
  },
  async clearBoughtShoppingItems() {
    return await request("/api/shopping/clear-bought", {
      method: "POST"
    });
  },

  // CSV Exports Helper
  getExportUrl(type) {
    const token = authStorage.getToken();
    return `${API_BASE}/api/exports/${type}.csv?token=${encodeURIComponent(token || "")}`;
  }
};
