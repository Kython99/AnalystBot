"""
AnalystBot — FastAPI entry point.
Handles: Telegram webhooks, health checks, Stripe webhooks, and static web serving.
"""
import os
import tempfile
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from dotenv import load_dotenv
load_dotenv()

from gateway.telegram import router as telegram_router
from payments.stripe_webhook import router as stripe_router

DATA_DIR = os.getenv("ANALYSTBOT_DATA_DIR", "/root/analystbot-data")
WEB_DIR = os.getenv("ANALYSTBOT_WEB_DIR", "web")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown hooks."""
    # Ensure data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"AnalystBot starting. Data dir: {DATA_DIR}")
    yield
    print("AnalystBot shutting down.")


app = FastAPI(
    title="AnalystBot",
    description="AI data analyst agent for businesses",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow Vercel frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://*.vercel.app", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(telegram_router, prefix="", tags=["Telegram"])
app.include_router(stripe_router, prefix="", tags=["Payments"])

# Health check (no auth required)
@app.get("/healthz")
async def health():
    return {"status": "ok", "service": "AnalystBot"}


@app.get("/readyz")
async def ready():
    return {"status": "ready"}


# Stripe checkout endpoint for frontend
from payments.stripe_utils import create_checkout_session
from fastapi import HTTPException

@app.post("/api/checkout")
async def checkout(body: dict):
    plan = body.get("plan", "starter")
    chat_id = body.get("chat_id")
    if not chat_id:
        raise HTTPException(status_code=400, detail="chat_id required")
    try:
        url = create_checkout_session(plan, chat_id)
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Web: serve landing/pricing pages
@app.get("/", response_class=HTMLResponse)
async def landing():
    """Serve the landing page."""
    index_path = os.path.join(WEB_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path) as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>AnalystBot</h1><p>Landing page coming soon.</p>")


@app.get("/pricing", response_class=HTMLResponse)
async def pricing():
    """Serve the pricing page."""
    pricing_path = os.path.join(WEB_DIR, "pricing.html")
    if os.path.exists(pricing_path):
        with open(pricing_path) as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Pricing</h1><p>Coming soon.</p>")


@app.get("/success", response_class=HTMLResponse)
async def success():
    """Serve the post-payment success page."""
    success_path = os.path.join(WEB_DIR, "success.html")
    if os.path.exists(success_path):
        with open(success_path) as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Payment Successful!</h1>")


# File upload endpoint (for tenant files via web)
@app.post("/upload/{tenant_id}")
async def upload_file(tenant_id: str, file: UploadFile = File(...)):
    """Upload a file for a tenant."""
    from tenants.context import TenantContext
    ctx = TenantContext(DATA_DIR)

    # Validate file type
    allowed = {".csv", ".xlsx", ".xls"}
    _, ext = os.path.splitext(file.filename)
    if ext.lower() not in allowed:
        raise HTTPException(status_code=400, detail=f"File type {ext} not allowed. Upload CSV or Excel.")

    # Save file
    content = await file.read()
    path = ctx.upload_file(tenant_id, file.filename, content)

    # Update config
    config = ctx.get_config(tenant_id)
    sources = config.get("data_sources", [])
    sources.append({"type": "file", "filename": file.filename, "label": file.filename})
    config["data_sources"] = sources
    ctx.save_config(tenant_id, config)

    return {"ok": True, "filename": file.filename, "path": path}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8766"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
