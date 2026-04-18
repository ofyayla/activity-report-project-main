# Storage Fallback Mechanism — MinIO + Local FS

Proje otomatik olarak MinIO'dan Local Filesystem'e geçer eğer MinIO ayakta değilse.

---

## 🏗️ Architecture

```
StorageManager (Orchestrator)
├─ Primary: MinIO (http://10.144.100.204:9000)
│  ├─ S3-compatible API
│  ├─ Versioning support
│  └─ Health check every 60s
│
└─ Fallback: Local FS (/data/reports)
   ├─ Direct filesystem access
   ├─ Zero dependencies
   └─ Always available
```

### Decision Tree

```
File Upload Request
  ↓
Check Current Backend Health
  ├─ Healthy? → Use it
  ├─ Degraded? → Switch to fallback
  └─ Fallback failed? → Error
```

---

## 📝 Implementation

### 1️⃣ Storage Service (apps/api/app/services/storage.py)

**Three Classes:**

```python
# Abstract interface
class StorageBackend(ABC):
    async def upload_file(bucket, key, data) → bool
    async def download_file(bucket, key) → bytes
    async def delete_file(bucket, key) → bool
    async def list_files(bucket, prefix) → list[str]
    async def health_check() → bool
    async def get_storage_type() → str
```

**Implementations:**

```python
# MinIO
class MinIOStorage(StorageBackend):
    def __init__(endpoint, access_key, secret_key, use_ssl)
    # Uses boto3 client

# Local FS
class LocalFileSystemStorage(StorageBackend):
    def __init__(base_path="/data/reports")
    # Uses pathlib
```

**Manager:**

```python
class StorageManager:
    def __init__(settings)
        # Initialize primary (MinIO) + fallback (Local FS)
        # Auto-detect unhealthy backend every 60s
    
    async def upload_file(bucket, key, data) → (bool, storage_type)
    async def download_file(bucket, key) → bytes
    async def get_storage_status() → dict  # Health info
```

---

### 2️⃣ API Routes (apps/api/app/api/routes/storage.py)

**Endpoints:**

```
POST   /api/v1/storage/upload/{bucket}
       → File upload with fallback

GET    /api/v1/storage/download/{bucket}/{key}
       → File download with fallback

DELETE /api/v1/storage/delete/{bucket}/{key}
       → File deletion

GET    /api/v1/storage/list/{bucket}
       → List files

GET    /api/v1/storage/health
       → Storage status (debug endpoint)
```

---

### 3️⃣ Health Endpoint Integration

**Updated:** apps/api/app/api/routes/health.py

```python
GET /health/ready

Response:
{
    "status": "ready",
    "checks": {
        "app": "ok",
        "database": "ok",
        "storage": "ok",  # or "fallback" if using local FS
        "storage_detail": {
            "primary": {
                "type": "MinIO",
                "healthy": false  # ← MinIO DOWN
            },
            "fallback": {
                "type": "Local FS",
                "healthy": true   # ← Using this
            },
            "current": "Local FS"
        }
    }
}
```

---

## 💡 Usage Examples

### Example 1: Simple Upload

```python
from fastapi import UploadFile
from app.services.storage import get_storage_manager

async def upload_report(file: UploadFile):
    storage = get_storage_manager()
    
    content = await file.read()
    success, backend = await storage.upload_file(
        bucket="report-uploads",
        key=file.filename,
        data=content
    )
    
    if success:
        print(f"✓ Uploaded to {backend}")  # MinIO or Local FS
    else:
        print("❌ Upload failed")
```

### Example 2: With Fallback Awareness

```python
async def save_and_notify(file_data: bytes, filename: str):
    storage = get_storage_manager()
    
    success, backend = await storage.upload_file(
        bucket="report-snapshots",
        key=filename,
        data=file_data
    )
    
    if backend == "Local FS":
        # Log warning if using fallback
        logger.warning(f"⚠️ Using local FS fallback for {filename}")
        # Maybe send alert to admin
        notify_ops(f"MinIO down, using local storage")
    
    return success
```

### Example 3: Download

```python
async def get_report(report_id: str):
    storage = get_storage_manager()
    
    data = await storage.download_file(
        bucket="report-snapshots",
        key=f"{report_id}.docx"
    )
    
    if data:
        return FileResponse(
            io.BytesIO(data),
            media_type="application/octet-stream"
        )
    else:
        raise HTTPException(404, "Report not found")
```

### Example 4: Storage Status (Admin)

```python
async def get_storage_status():
    storage = get_storage_manager()
    status = await storage.get_storage_status()
    
    return {
        "current": status["current"],
        "primary": status["primary"],
        "fallback": status["fallback"],
        "message": (
            "✓ MinIO operational"
            if status["current"] == "MinIO"
            else "⚠️ Using fallback (MinIO unavailable)"
        )
    }
```

---

## 🔄 Fallback Behavior Details

### Automatic Switching

```python
# Health check runs every 60 seconds
# If primary fails, switches to fallback

StorageManager._check_health()
│
├─ If using MinIO:
│  ├─ Try health_check()
│  └─ If fails: switch to Local FS
│
└─ If using Local FS:
   ├─ Monitor MinIO recovery
   └─ If MinIO recovers: switch back
```

### Dual Write (Optional Enhancement)

```python
# Write to both backends for safety
async def upload_file_with_backup(bucket, key, data):
    success1 = await primary.upload(bucket, key, data)
    success2 = await fallback.upload(bucket, key, data)
    
    # Both succeed or rollback?
    return success1 and success2
```

### Eventual Consistency

```
Scenario: MinIO comes back online while Local FS is in use

Timeline:
1. 10:00 - MinIO goes down → Switch to Local FS
2. 10:05 - Files uploaded to Local FS
3. 10:30 - MinIO recovers → Switch back to MinIO
4. 10:35 - New files go to MinIO
5. 10:40 - Sync task copies Local FS files to MinIO

Risk: Split-brain (some files in Local FS, some in MinIO)

Mitigation: 
- Background sync job (cron: rsync or S3Sync)
- Or: Keep both in sync (dual-write)
```

---

## ⚙️ Configuration

### .env

```env
# Storage type
STORAGE_USE_LOCAL=false  # true = skip MinIO, use local FS only

# MinIO (primary)
MINIO_ENDPOINT=http://10.144.100.204:9000
MINIO_ACCESS_KEY=your-key
MINIO_SECRET_KEY=your-secret
MINIO_USE_SSL=false

# Local FS (fallback)
LOCAL_STORAGE_ROOT=/data/reports
```

### Initialization

```python
# apps/api/app/core/settings.py
class Settings(BaseSettings):
    storage_use_local: bool = Field(default=True)
    minio_endpoint: str = Field(default="http://10.144.100.204:9000")
    minio_access_key: str = Field(default=None)
    minio_secret_key: str = Field(default=None)
    minio_use_ssl: bool = Field(default=False)
    local_storage_root: str = Field(default="/data/reports")
```

---

## 🧪 Testing Fallback

### Test 1: Stop MinIO, verify fallback

```bash
# Terminal 1: Start API
cd apps/api
uvicorn app.main:app --reload

# Terminal 2: Upload file
curl -X POST http://10.144.100.204:8000/api/v1/storage/upload/report-uploads \
  -F "file=@test.xlsx"

# Response (MinIO working):
# {"storage": "MinIO", "status": "success"}

# Now stop MinIO
sudo systemctl stop minio

# Wait 60s (health check interval)
sleep 65

# Upload again
curl -X POST http://10.144.100.204:8000/api/v1/storage/upload/report-uploads \
  -F "file=@test2.xlsx"

# Response (fallback active):
# {"storage": "Local FS", "status": "success"}

# Check health endpoint
curl http://10.144.100.204:8000/health/ready

# Notice: "storage": "fallback", "current": "Local FS"
```

### Test 2: Restart MinIO, verify recovery

```bash
# Restart MinIO
sudo systemctl start minio

# Wait 60s
sleep 65

# Next upload should go back to MinIO
curl -X POST http://10.144.100.204:8000/api/v1/storage/upload/report-uploads \
  -F "file=@test3.xlsx"

# Response:
# {"storage": "MinIO", "status": "success"}

# Health shows recovery
curl http://10.144.100.204:8000/health/ready
# "current": "MinIO"
```

---

## 📊 Production Considerations

### Monitoring

```python
# Add to monitoring/alerting
async def check_storage():
    storage = get_storage_manager()
    status = await storage.get_storage_status()
    
    if status["current"] == "Local FS":
        alert("⚠️ Using fallback storage", severity="warning")
        alert("MinIO is down", severity="critical")
```

### Sync Strategy

```python
# Cron job (daily): Sync local FS to MinIO
@app.on_event("startup")
async def setup_storage_sync():
    # Copy any files from Local FS → MinIO
    # (For when MinIO recovers)
    pass
```

### Quotas

```python
# Set limits to prevent disk fill-up
LOCAL_STORAGE_MAX_SIZE = 500_000_000_000  # 500 GB
MINIO_BUCKET_QUOTA = 1_000_000_000_000    # 1 TB
```

### Backup

```bash
# Backup local FS
rsync -av /data/reports/ /backup/reports/

# Backup MinIO
mc mirror --watch minio/report-uploads /backup/minio-uploads/
```

---

## 🚀 Deployment Checklist

- [ ] Storage service initialized in FastAPI
- [ ] Routes added to API router
- [ ] Health endpoint shows storage status
- [ ] MinIO configured and running
- [ ] Local FS directory created (`/data/reports`)
- [ ] `.env` configured with credentials
- [ ] Test upload/download with MinIO online
- [ ] Stop MinIO and test fallback
- [ ] Restart MinIO and verify recovery
- [ ] Health endpoint shows correct status
- [ ] Logs show fallback detection messages

---

## 🔗 Related Files

- [apps/api/app/services/storage.py](file:apps/api/app/services/storage.py) — Storage abstraction
- [apps/api/app/api/routes/storage.py](file:apps/api/app/api/routes/storage.py) — API endpoints
- [apps/api/app/api/routes/health.py](file:apps/api/app/api/routes/health.py) — Health checks
- [MINIO-LINUX-QUICKSTART.md](file:MINIO-LINUX-QUICKSTART.md) — MinIO setup
- [MINIO-ALTERNATIVES.md](file:MINIO-ALTERNATIVES.md) — Storage options
