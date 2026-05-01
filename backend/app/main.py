import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from .api import dashboard, demo, fraud, transactions, verification
from .config import get_settings
from .database import Base, engine
from .models import fraud_alert, transaction
from .websocket import ws_manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)
settings = get_settings()
limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.rate_limit_per_minute}/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    logger.info("SimGuard started with integration mode %s", settings.integration_mode)
    yield
    logger.info("SimGuard shutting down")


app = FastAPI(
    title="SimGuard API",
    description="Real-time SIM Swap Fraud Prevention for Mobile Money",
    version="1.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.app_env == "development" else None,
    redoc_url="/redoc" if settings.app_env == "development" else None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def enforce_payload_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > settings.max_payload_size:
        return JSONResponse(
            status_code=413,
            content={"detail": f"Payload too large. Max {settings.max_payload_size // 1024} KB."},
        )
    return await call_next(request)


app.include_router(transactions.router)
app.include_router(fraud.router)
app.include_router(dashboard.router)
app.include_router(verification.router)
app.include_router(demo.router)


@app.websocket("/ws/alerts")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as exc:
        logger.warning("WebSocket error: %s", exc)
        ws_manager.disconnect(websocket)


@app.get("/health")
def health():
    return {"status": "ok", "service": "simguard", "version": "1.1.0", "integration_mode": settings.integration_mode}


@app.get("/")
def root():
    return {"message": "SimGuard API - Real-time SIM Swap Fraud Prevention", "integration_mode": settings.integration_mode}
