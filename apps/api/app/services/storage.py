"""
Storage Service — MinIO with Local FS Fallback

Eğer MinIO ayakta değilse, automatically local filesystem'e geçer.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Tuple
import logging
import asyncio
from datetime import datetime, timedelta
import hashlib

from minio import Minio
from minio.error import S3Error

from app.core.settings import settings

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """Abstract storage interface"""

    @abstractmethod
    async def upload_file(self, bucket: str, key: str, data: bytes) -> bool:
        """Upload file to bucket"""
        pass

    @abstractmethod
    async def download_file(self, bucket: str, key: str) -> Optional[bytes]:
        """Download file from bucket"""
        pass

    @abstractmethod
    async def delete_file(self, bucket: str, key: str) -> bool:
        """Delete file from bucket"""
        pass

    @abstractmethod
    async def list_files(self, bucket: str, prefix: str = "") -> list[str]:
        """List files in bucket"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if storage is healthy"""
        pass

    @abstractmethod
    def get_storage_type(self) -> str:
        """Return storage type name"""
        pass


class MinIOStorage(StorageBackend):
    """MinIO S3-compatible storage"""

    def __init__(self, endpoint: str, access_key: str, secret_key: str, use_ssl: bool = False):
        self.endpoint = endpoint.replace("http://", "").replace("https://", "")
        self.access_key = access_key
        self.secret_key = secret_key
        self.use_ssl = use_ssl

        try:
            self.client = Minio(
                self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.use_ssl
            )
            logger.info(f"MinIO client initialized: {self.endpoint}")
        except Exception as e:
            logger.error(f"MinIO initialization error: {e}")
            self.client = None

    async def upload_file(self, bucket: str, key: str, data: bytes) -> bool:
        """Upload file to MinIO bucket"""
        if not self.client:
            logger.warning("MinIO client not available")
            return False

        try:
            # Ensure bucket exists
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)
                logger.info(f"Created bucket: {bucket}")

            # Upload
            self.client.put_object(
                bucket,
                key,
                data=data,
                length=len(data)
            )
            logger.info(f"Uploaded {key} to {bucket}")
            return True

        except S3Error as e:
            logger.error(f"MinIO upload error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error uploading to MinIO: {e}")
            return False

    async def download_file(self, bucket: str, key: str) -> Optional[bytes]:
        """Download file from MinIO bucket"""
        if not self.client:
            logger.warning("MinIO client not available")
            return None

        try:
            response = self.client.get_object(bucket, key)
            data = response.read()
            response.close()
            return data

        except S3Error as e:
            logger.error(f"MinIO download error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading from MinIO: {e}")
            return None

    async def delete_file(self, bucket: str, key: str) -> bool:
        """Delete file from MinIO bucket"""
        if not self.client:
            return False

        try:
            self.client.remove_object(bucket, key)
            logger.info(f"Deleted {key} from {bucket}")
            return True
        except S3Error as e:
            logger.error(f"MinIO delete error: {e}")
            return False

    async def list_files(self, bucket: str, prefix: str = "") -> list[str]:
        """List files in MinIO bucket"""
        if not self.client:
            return []

        try:
            objects = self.client.list_objects(bucket, prefix=prefix)
            return [obj.object_name for obj in objects]
        except S3Error as e:
            logger.error(f"MinIO list error: {e}")
            return []

    async def health_check(self) -> bool:
        """Check MinIO health"""
        if not self.client:
            return False

        try:
            # Simple connectivity test
            self.client.list_buckets()
            return True
        except Exception as e:
            logger.warning(f"MinIO health check failed: {e}")
            return False

    def get_storage_type(self) -> str:
        return "MinIO"


class LocalFileSystemStorage(StorageBackend):
    """Local filesystem storage (fallback)"""

    def __init__(self, base_path: str = "/data/reports"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Local FS storage initialized: {self.base_path}")

    async def upload_file(self, bucket: str, key: str, data: bytes) -> bool:
        """Save file to local filesystem"""
        try:
            bucket_path = self.base_path / bucket
            bucket_path.mkdir(parents=True, exist_ok=True)

            file_path = bucket_path / key
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(data)

            logger.info(f"Saved {key} to local FS: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Local FS upload error: {e}")
            return False

    async def download_file(self, bucket: str, key: str) -> Optional[bytes]:
        """Read file from local filesystem"""
        try:
            file_path = self.base_path / bucket / key
            if file_path.exists():
                return file_path.read_bytes()

            logger.warning(f"File not found: {file_path}")
            return None

        except Exception as e:
            logger.error(f"Local FS download error: {e}")
            return None

    async def delete_file(self, bucket: str, key: str) -> bool:
        """Delete file from local filesystem"""
        try:
            file_path = self.base_path / bucket / key
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted local file: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Local FS delete error: {e}")
            return False

    async def list_files(self, bucket: str, prefix: str = "") -> list[str]:
        """List files in local bucket"""
        try:
            bucket_path = self.base_path / bucket
            if not bucket_path.exists():
                return []

            files = []
            for item in bucket_path.rglob("*"):
                if item.is_file():
                    rel_path = item.relative_to(bucket_path).as_posix()
                    if prefix == "" or rel_path.startswith(prefix):
                        files.append(rel_path)

            return files

        except Exception as e:
            logger.error(f"Local FS list error: {e}")
            return []

    async def health_check(self) -> bool:
        """Check local FS health"""
        try:
            # Try to write a test file
            test_file = self.base_path / ".health-check"
            test_file.write_text(str(datetime.utcnow()))
            test_file.unlink()
            return True
        except Exception as e:
            logger.warning(f"Local FS health check failed: {e}")
            return False

    def get_storage_type(self) -> str:
        return "Local FS"


class StorageManager:
    """Storage manager with automatic fallback"""

    def __init__(self, settings):
        self.settings = settings
        self.primary: Optional[StorageBackend] = None
        self.fallback: Optional[StorageBackend] = None
        self.current_backend: Optional[StorageBackend] = None
        self.health_check_interval = 60  # seconds
        self.last_health_check = 0

        self._initialize_backends()

    def _initialize_backends(self):
        """Initialize primary and fallback backends"""

        # Primary: MinIO (if configured)
        if not self.settings.storage_use_local and self.settings.minio_endpoint:
            try:
                endpoint = self.settings.minio_endpoint
                self.primary = MinIOStorage(
                    endpoint=endpoint,
                    access_key=self.settings.minio_access_key or "minioadmin",
                    secret_key=self.settings.minio_secret_key or "minioadmin",
                    use_ssl=self.settings.minio_use_ssl
                )
                logger.info("Primary backend: MinIO")
            except Exception as e:
                logger.warning(f"MinIO initialization failed, using fallback: {e}")
                self.primary = None

        # Fallback: Local FS (always available)
        try:
            local_root = self.settings.local_storage_root or "/data/reports"
            self.fallback = LocalFileSystemStorage(base_path=local_root)
            logger.info(f"Fallback backend: Local FS ({local_root})")
        except Exception as e:
            logger.error(f"Failed to initialize fallback storage: {e}")

        # Set current backend
        self.current_backend = self.primary or self.fallback
        if self.current_backend:
            logger.info(f"Using storage: {self.current_backend.get_storage_type()}")

    async def _check_health(self):
        """Check health and switch if needed"""
        now = datetime.utcnow().timestamp()

        # Skip if checked recently
        if now - self.last_health_check < self.health_check_interval:
            return

        self.last_health_check = now

        # If using primary, check if it's healthy
        if self.current_backend == self.primary and self.primary:
            if not await self.primary.health_check():
                logger.warning("Primary backend unhealthy, switching to fallback")
                self.current_backend = self.fallback
                return

        # If using fallback, check if primary recovered
        if self.current_backend == self.fallback and self.primary:
            if await self.primary.health_check():
                logger.info("Primary backend recovered, switching back")
                self.current_backend = self.primary

    async def upload_file(self, bucket: str, key: str, data: bytes) -> Tuple[bool, str]:
        """Upload file with automatic fallback"""
        await self._check_health()

        if not self.current_backend:
            return False, "No storage backend available"

        # Try current backend
        success = await self.current_backend.upload_file(bucket, key, data)

        if success:
            return True, self.current_backend.get_storage_type()

        # If primary failed and fallback available, try fallback
        if self.current_backend != self.fallback and self.fallback:
            logger.warning(f"Primary upload failed, trying fallback")
            success = await self.fallback.upload_file(bucket, key, data)
            if success:
                self.current_backend = self.fallback
                return True, self.fallback.get_storage_type()

        return False, f"Upload failed on {self.current_backend.get_storage_type()}"

    async def download_file(self, bucket: str, key: str) -> Optional[bytes]:
        """Download file with automatic fallback"""
        await self._check_health()

        if not self.current_backend:
            return None

        # Try current backend
        data = await self.current_backend.download_file(bucket, key)
        if data is not None:
            return data

        # If primary failed and fallback available, try fallback
        if self.current_backend != self.fallback and self.fallback:
            logger.warning(f"Primary download failed, trying fallback")
            data = await self.fallback.download_file(bucket, key)
            if data is not None:
                self.current_backend = self.fallback
                return data

        return None

    async def delete_file(self, bucket: str, key: str) -> bool:
        """Delete file from current backend"""
        await self._check_health()

        if not self.current_backend:
            return False

        success = await self.current_backend.delete_file(bucket, key)

        # Also delete from fallback if using primary
        if success and self.current_backend != self.fallback and self.fallback:
            await self.fallback.delete_file(bucket, key)

        return success

    async def list_files(self, bucket: str, prefix: str = "") -> list[str]:
        """List files from current backend"""
        await self._check_health()

        if not self.current_backend:
            return []

        return await self.current_backend.list_files(bucket, prefix)

    async def get_storage_status(self) -> dict:
        """Get storage status for health endpoint"""
        primary_healthy = await self.primary.health_check() if self.primary else False
        fallback_healthy = await self.fallback.health_check() if self.fallback else False

        return {
            "primary": {
                "type": self.primary.get_storage_type() if self.primary else "None",
                "healthy": primary_healthy
            },
            "fallback": {
                "type": self.fallback.get_storage_type() if self.fallback else "None",
                "healthy": fallback_healthy
            },
            "current": self.current_backend.get_storage_type() if self.current_backend else "None"
        }


# Global storage manager instance
_storage_manager: Optional[StorageManager] = None


def get_storage_manager() -> StorageManager:
    """Get or create storage manager"""
    global _storage_manager

    if _storage_manager is None:
        _storage_manager = StorageManager(settings)

    return _storage_manager
