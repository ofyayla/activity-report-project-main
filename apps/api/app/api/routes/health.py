# Health check endpoints with storage fallback detection

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session
import logging

from app.db.session import get_db
from app.schemas.health import LivenessResponse, ReadinessResponse
from app.services.storage import get_storage_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", response_model=LivenessResponse)
async def liveness() -> LivenessResponse:
    return LivenessResponse(status="alive", service="api")


@router.get("/ready", response_model=ReadinessResponse)
async def readiness(db: Session = Depends(get_db)) -> ReadinessResponse:
    checks = {"app": "ok"}

    # Database check
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = "error"
        logger.error(f"Database health check failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_ready",
                "checks": checks,
                "reason": f"Database error: {str(exc)}",
            },
        ) from exc

    # Storage check (with fallback detection)
    try:
        storage = get_storage_manager()
        storage_status = await storage.get_storage_status()

        if storage_status["current"] == "Local FS" and storage_status["primary"]["type"] == "MinIO":
            logger.warning("Using fallback storage (MinIO unavailable)")
            checks["storage"] = "fallback"  # OK but on fallback
            checks["storage_detail"] = storage_status
        else:
            checks["storage"] = "ok"
            checks["storage_detail"] = storage_status

    except Exception as exc:
        checks["storage"] = "error"
        logger.error(f"Storage health check failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_ready",
                "checks": checks,
                "reason": f"Storage error: {str(exc)}",
            },
        ) from exc

    return ReadinessResponse(status="ready", checks=checks)
