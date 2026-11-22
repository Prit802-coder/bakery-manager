import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from backend.database import engine, Base
from backend.seed import seed_database
from backend.routers import (
    auth, sales, purchases, inventory, recipes, shopping, dashboard, exports
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database schema is created and initial seed data exists
    Base.metadata.create_all(bind=engine)
    try:
        seed_database()
    except Exception as e:
        print(f"Startup seed notice: {e}")
    yield

app = FastAPI(
    title="Mom's Homemade Cake Business Manager",
    description="Private, phone-friendly business manager for in-person homemade cake sales, purchases, recipes, baking, and stock tracking.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(sales.router)
app.include_router(purchases.router)
app.include_router(inventory.router)
app.include_router(recipes.router)
app.include_router(shopping.router)
app.include_router(exports.router)

# Mount frontend static directory if exists
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/")
def serve_index():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Mom's Cake Business Manager API is running. Frontend not found."}

@app.get("/health")
def health_check():
    return {"status": "ok", "app": "Mom's Homemade Cake Business Manager"}
