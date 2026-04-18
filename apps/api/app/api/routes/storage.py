"""
Storage API Routes — File upload/download with MinIO fallback
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
import io
import logging

from app.services.storage import get_storage_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/storage", tags=["storage"])


@router.post("/upload/{bucket}")
async def upload_file(bucket: str, file: UploadFile = File(...)) -> dict:
    """
    Upload file to storage (MinIO with local FS fallback)

    Example:
        POST /api/v1/storage/upload/report-uploads
        Content-Type: multipart/form-data
        file: <binary>

    Response:
        {
            "filename": "report.xlsx",
            "bucket": "report-uploads",
            "storage": "MinIO",
            "size": 1024000,
            "status": "success"
        }
    """
    storage = get_storage_manager()

    try:
        # Read file
        content = await file.read()
        file_size = len(content)

        # Upload
        success, storage_type = await storage.upload_file(bucket, file.filename, content)

        if not success:
            raise HTTPException(status_code=500, detail=f"Upload failed: {storage_type}")

        logger.info(f"File uploaded: {file.filename} ({file_size} bytes) → {storage_type}")

        return {
            "filename": file.filename,
            "bucket": bucket,
            "storage": storage_type,
            "size": file_size,
            "status": "success"
        }

    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{bucket}/{key:path}")
async def download_file(bucket: str, key: str):
    """
    Download file from storage (MinIO with local FS fallback)

    Example:
        GET /api/v1/storage/download/report-snapshots/report-2025-01.docx

    Returns: Binary file content
    """
    storage = get_storage_manager()

    try:
        data = await storage.download_file(bucket, key)

        if data is None:
            raise HTTPException(status_code=404, detail="File not found")

        # Stream response
        return StreamingResponse(
            io.BytesIO(data),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={key}"}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete/{bucket}/{key:path}")
async def delete_file(bucket: str, key: str) -> dict:
    """
    Delete file from storage

    Example:
        DELETE /api/v1/storage/delete/report-uploads/old-file.xlsx

    Response:
        {
            "filename": "old-file.xlsx",
            "bucket": "report-uploads",
            "status": "deleted"
        }
    """
    storage = get_storage_manager()

    try:
        success = await storage.delete_file(bucket, key)

        if not success:
            raise HTTPException(status_code=500, detail="Delete failed")

        logger.info(f"File deleted: {key} from {bucket}")

        return {
            "filename": key,
            "bucket": bucket,
            "status": "deleted"
        }

    except Exception as e:
        logger.error(f"Delete error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list/{bucket}")
async def list_files(bucket: str, prefix: str = "") -> dict:
    """
    List files in bucket

    Example:
        GET /api/v1/storage/list/report-uploads?prefix=2025

    Response:
        {
            "bucket": "report-uploads",
            "prefix": "2025",
            "files": [
                "2025-01-report.xlsx",
                "2025-02-report.xlsx"
            ]
        }
    """
    storage = get_storage_manager()

    try:
        files = await storage.list_files(bucket, prefix)

        return {
            "bucket": bucket,
            "prefix": prefix,
            "files": files,
            "count": len(files)
        }

    except Exception as e:
        logger.error(f"List error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def storage_health() -> dict:
    """
    Storage health status

    Returns:
        {
            "primary": {
                "type": "MinIO",
                "healthy": true
            },
            "fallback": {
                "type": "Local FS",
                "healthy": true
            },
            "current": "MinIO"
        }
    """
    storage = get_storage_manager()
    status = await storage.get_storage_status()
    return status
