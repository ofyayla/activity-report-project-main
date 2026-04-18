# MinIO Standalone Setup — Veni AI Report Factory

Bu rehber, **standalone (Docker olmadan)** MinIO binary ile on-premise ortamında object storage kurulumunu anlatır.

---

## 1. MinIO Nedir ve Neden Kullanıyoruz?

- **S3-compatible** object storage (AWS S3 API emülasyonu)
- Excel uploads, report snapshots, images depolama
- Açık kaynak, on-premise uyumlu
- HTTP REST API ve web console

**Projede Kullanım:**
```
Uploaded Files (Excel) → MinIO bucket: report-uploads
Published Report Snapshots → MinIO bucket: report-snapshots
Generated Images, Logs → MinIO bucket: report-uploads
```

---

## 2. Kurulum Adımları

### 2.1 MinIO Binary İndirin

**Linux (x86_64):**
```bash
cd /opt
wget https://dl.min.io/server/minio/release/linux-amd64/minio
chmod +x minio
```

**macOS (Intel):**
```bash
cd /opt
wget https://dl.min.io/server/minio/release/darwin-amd64/minio
chmod +x minio
```

**macOS (M1/M2):**
```bash
cd /opt
wget https://dl.min.io/server/minio/release/darwin-arm64/minio
chmod +x minio
```

**Windows:**
```powershell
# https://dl.min.io/server/minio/release/windows-amd64/minio.exe adresinden indir
# C:\minio\ klasörüne koy
```

### 2.2 Data Dizini Oluştur

```bash
# Linux/macOS
mkdir -p /data/minio
chmod 700 /data/minio

# Windows
mkdir C:\minio-data
```

### 2.3 Standalone Mode'da Başlat

**Linux/macOS — Foreground:**
```bash
/opt/minio server /data/minio --console-address :9001
```

**Output:**
```
  API: http://10.144.100.204:9000  http://127.0.0.1:9000
  RootUser: minioadmin
  RootPass: minioadmin
  Web Console: http://10.144.100.204:9001
```

**Port Açıklaması:**
- `9000` — S3 API endpoint (Python SDK kullanacağız)
- `9001` — Web console (admin panel, bucket/policy setup)

### 2.4 Windows — Service Olarak Başlat (NSSM)

NSSM (Non-Sucking Service Manager) kullan:

```powershell
# NSSM indir
# https://nssm.cc/download adresinden `nssm.exe`'i C:\nssm\ altına koy

cd C:\nssm
.\nssm.exe install MinIOServer C:\minio\minio.exe
.\nssm.exe set MinIOServer AppParameters "server C:\minio-data --console-address :9001"
.\nssm.exe start MinIOServer

# Durumu kontrol et
.\nssm.exe status MinIOServer
```

### 2.5 Linux — Systemd Service Olarak Başlat

```bash
sudo tee /etc/systemd/system/minio.service > /dev/null <<'EOF'
[Unit]
Description=MinIO
After=network.target

[Service]
Type=simple
User=minio
ExecStart=/opt/minio server /data/minio --console-address :9001
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# minio user oluştur
sudo useradd -r -s /sbin/nologin minio
sudo chown -R minio:minio /data/minio

# Service başlat
sudo systemctl enable minio
sudo systemctl start minio
sudo systemctl status minio
```

---

## 3. Web Console'da Setup

### 3.1 Console'a Gir

```
URL: http://10.144.100.204:9001
RootUser: minioadmin
RootPass: minioadmin
```

### 3.2 Access Key Oluştur

1. **Admin Console** açın → http://10.144.100.204:9001
2. Sol menü: **Access Keys** → **Create Access Key**
3. Generate et:
   - **Access Key:** `veni-report-user` (örnek)
   - **Secret Key:** (Auto-generated, güvenli sakla)

Örnek output:
```
Access Key: AKIAIOSFODNN7EXAMPLE
Secret Key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

**⚠️ Not:** Secret key'i `.env` dosyasında kullan. Hiçbir yerde commit etme!

### 3.3 Buckets Oluştur

**Yönetim Console'dan:**
1. **Buckets** → **Create Bucket**
2. İki bucket oluştur:
   - `report-uploads` (Excel, images)
   - `report-snapshots` (published reports)
3. Her bucket için **Public** ayarını kontrol et (projede private tutacağız)

**Command line ile (mc client):**

```bash
# mc indir
wget https://dl.min.io/client/mc/release/linux-amd64/mc
chmod +x mc

# MinIO'ya bağlan
./mc alias set minio http://10.144.100.204:9000 minioadmin minioadmin

# Buckets oluştur
./mc mb minio/report-uploads
./mc mb minio/report-snapshots

# Policy ayarla (private)
./mc policy set private minio/report-uploads
./mc policy set private minio/report-snapshots

# Versioning aç (optional, snapshot recovery için)
./mc version enable minio/report-snapshots
```

### 3.4 CORS Rules Ayarla

Web frontend'den direct S3 upload yapacaksanız CORS gerekir. Örnek:

```bash
# CORS policy JSON
cat > cors.json <<'EOF'
{
  "CORSRules": [
    {
      "AllowedMethods": ["GET", "PUT", "POST"],
      "AllowedOrigins": ["http://10.144.100.204:48000"],
      "AllowedHeaders": ["*"],
      "MaxAgeSeconds": 3000
    }
  ]
}
EOF

# MinIO'ya apply et
./mc cors set cors.json minio/report-uploads
./mc cors set cors.json minio/report-snapshots
```

---

## 4. Python SDK'dan Kullanım

### 4.1 Boto3 (AWS S3 SDK)

```python
import boto3

# MinIO bağlantısı (S3-compatible)
s3_client = boto3.client(
    's3',
    endpoint_url='http://10.144.100.204:9000',
    aws_access_key_id='AKIAIOSFODNN7EXAMPLE',
    aws_secret_access_key='wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
    region_name='us-east-1'  # MinIO için dummy
)

# File upload
response = s3_client.put_object(
    Bucket='report-uploads',
    Key='excel-2025.xlsx',
    Body=open('/path/to/file.xlsx', 'rb')
)
print(f"Uploaded: {response['ETag']}")

# File download
s3_client.download_file('report-snapshots', 'report-2025.docx', '/tmp/report.docx')

# List buckets
buckets = s3_client.list_buckets()
for bucket in buckets['Buckets']:
    print(bucket['Name'])
```

### 4.2 Minio-py (Native MinIO SDK)

```python
from minio import Minio
from minio.error import S3Error

# MinIO client
minio_client = Minio(
    "10.144.100.204:9000",
    access_key="AKIAIOSFODNN7EXAMPLE",
    secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    secure=False  # HTTP (not HTTPS)
)

# File upload
try:
    minio_client.fput_object(
        "report-uploads",
        "excel-2025.xlsx",
        "/path/to/file.xlsx"
    )
    print("File uploaded successfully")
except S3Error as exc:
    print(f"Upload error: {exc}")

# List objects
try:
    objects = minio_client.list_objects("report-uploads", recursive=True)
    for obj in objects:
        print(obj.object_name)
except S3Error as exc:
    print(f"List error: {exc}")
```

### 4.3 FastAPI Integration

```python
# apps/api/app/services/storage.py (örnek)

from minio import Minio
from minio.error import S3Error
import os

class MinIOStorage:
    def __init__(self):
        self.client = Minio(
            os.getenv("MINIO_ENDPOINT", "10.144.100.204:9000").replace("http://", "").replace("https://", ""),
            access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
            secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
            secure=os.getenv("MINIO_USE_SSL", "false").lower() == "true"
        )
    
    def upload_file(self, bucket: str, object_name: str, file_path: str) -> bool:
        try:
            self.client.fput_object(bucket, object_name, file_path)
            return True
        except S3Error as e:
            print(f"MinIO error: {e}")
            return False
    
    def download_file(self, bucket: str, object_name: str, file_path: str) -> bool:
        try:
            self.client.fdownload_object(bucket, object_name, file_path)
            return True
        except S3Error as e:
            print(f"MinIO error: {e}")
            return False
    
    def generate_presigned_url(self, bucket: str, object_name: str, expires_in: int = 3600) -> str:
        """Temporary download URL"""
        try:
            url = self.client.get_presigned_download_url(bucket, object_name, expires_in)
            return url
        except S3Error as e:
            print(f"MinIO error: {e}")
            return None

# FastAPI route
from fastapi import UploadFile, File

storage = MinIOStorage()

@app.post("/api/v1/upload/excel")
async def upload_excel(file: UploadFile = File(...)):
    temp_path = f"/tmp/{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(await file.read())
    
    if storage.upload_file("report-uploads", file.filename, temp_path):
        os.remove(temp_path)
        return {"status": "ok", "filename": file.filename}
    return {"error": "Upload failed"}, 400
```

---

## 5. Environment Variables Setup

### .env Dosyasına Ekle

```env
STORAGE_USE_LOCAL=false
MINIO_ENDPOINT=http://10.144.100.204:9000
MINIO_ACCESS_KEY=veni-report-user
MINIO_SECRET_KEY=your-secret-key-here
MINIO_USE_SSL=false
MINIO_BUCKET_UPLOADS=report-uploads
MINIO_BUCKET_SNAPSHOTS=report-snapshots
```

### settings.py'de Read Et

```python
class Settings(BaseSettings):
    storage_use_local: bool = Field(default=True)
    minio_endpoint: str | None = Field(default="http://10.144.100.204:9000")
    minio_access_key: str | None = Field(default=None)
    minio_secret_key: str | None = Field(default=None)
    minio_use_ssl: bool = Field(default=False)
    minio_bucket_uploads: str = Field(default="report-uploads")
    minio_bucket_snapshots: str = Field(default="report-snapshots")
```

---

## 6. Standalone Deployment — Script

Tüm servisleri standalone ayağa kaldırmak için script:

**start-services.sh (Linux/macOS):**

```bash
#!/bin/bash

set -e

# MinIO
echo "▶ Starting MinIO..."
/opt/minio server /data/minio --console-address :9001 &
MINIO_PID=$!
sleep 2

# PostgreSQL + pgvector (remote'da zaten ayakta)
echo "✓ PostgreSQL: 10.144.100.204:25432"

# Redis (remote'da zaten ayakta)
echo "✓ Redis: 10.144.100.204:46379"

# vLLM (external, shared GPU)
echo "✓ vLLM: 10.144.100.204:8821"

# Jina Embedding (internal domain)
echo "✓ Jina: jina-embedding.aiops.albarakaturk.local"

# API (FastAPI)
echo "▶ Starting FastAPI API..."
cd apps/api
export DATABASE_URL=postgresql+asyncpg://vector_user1:${PGVECTOR_PASSWORD}@10.144.100.204:25432/vectordb1
export REDIS_URL=redis://:${REDIS_PASSWORD}@10.144.100.204:46379/0
export MINIO_ENDPOINT=http://10.144.100.204:9000
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!
sleep 3

# Worker (ARQ)
echo "▶ Starting ARQ Worker..."
cd ../..
services/worker/venv/bin/python -m arq services.worker.app.WorkerSettings &
WORKER_PID=$!
sleep 2

# Hocuspocus (Node.js realtime collab)
echo "▶ Starting Hocuspocus Server..."
cd apps/collab-server
npm install
HOCUSPOCUS_JWT_SECRET=dev-secret npm start &
HOCUSPOCUS_PID=$!
sleep 3

# Frontend (Next.js)
echo "▶ Starting Next.js Frontend..."
cd ../../
export NEXT_PUBLIC_API_BASE_URL=http://10.144.100.204:8000
export NEXT_PUBLIC_APP_BASE_URL=http://10.144.100.204:48000
export NEXT_PUBLIC_HOCUSPOCUS_URL=ws://10.144.100.204:1234
pnpm --filter web dev --hostname 0.0.0.0 --port 48000 &
WEB_PID=$!

echo ""
echo "════════════════════════════════════════════════════"
echo "✅ All services started!"
echo "════════════════════════════════════════════════════"
echo ""
echo "API:                 http://10.144.100.204:8000"
echo "Frontend:            http://10.144.100.204:48000"
echo "MinIO Console:       http://10.144.100.204:9001"
echo "Hocuspocus WebSocket: ws://10.144.100.204:1234"
echo ""
echo "PIDs:"
echo "  MinIO:       $MINIO_PID"
echo "  API:         $API_PID"
echo "  Worker:      $WORKER_PID"
echo "  Hocuspocus:  $HOCUSPOCUS_PID"
echo "  Frontend:    $WEB_PID"
echo ""
echo "Stop all: kill $MINIO_PID $API_PID $WORKER_PID $HOCUSPOCUS_PID $WEB_PID"
echo ""

# Wait for any to fail
wait -n
exit $?
```

**start-services.bat (Windows):**

```batch
@echo off
setlocal enabledelayedexpansion

echo Starting all services...

REM MinIO (NSSM service ile zaten running olmalı)
echo ✓ MinIO: http://10.144.100.204:9000

REM PostgreSQL, Redis, vLLM (remote)
echo ✓ PostgreSQL: 10.144.100.204:25432
echo ✓ Redis: 10.144.100.204:46379
echo ✓ vLLM: 10.144.100.204:8821

REM API
echo ▶ Starting FastAPI...
cd apps\api
set DATABASE_URL=postgresql+asyncpg://vector_user1:PASSWORD@10.144.100.204:25432/vectordb1
set REDIS_URL=redis://:PASSWORD@10.144.100.204:46379/0
set MINIO_ENDPOINT=http://10.144.100.204:9000
alembic upgrade head
start "FastAPI" python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
cd ..\..

REM Worker
echo ▶ Starting Worker...
start "Worker" python -m arq services.worker.app.WorkerSettings

REM Hocuspocus
echo ▶ Starting Hocuspocus...
cd apps\collab-server
npm install
start "Hocuspocus" npm start
cd ..\..

REM Frontend
echo ▶ Starting Frontend...
set NEXT_PUBLIC_API_BASE_URL=http://10.144.100.204:8000
set NEXT_PUBLIC_APP_BASE_URL=http://10.144.100.204:48000
set NEXT_PUBLIC_HOCUSPOCUS_URL=ws://10.144.100.204:1234
start "Frontend" pnpm --filter web dev --hostname 0.0.0.0 --port 48000

echo.
echo ════════════════════════════════════════════════════
echo ✅ All services started!
echo ════════════════════════════════════════════════════
echo.
echo API:              http://10.144.100.204:8000
echo Frontend:         http://10.144.100.204:48000
echo MinIO Console:    http://10.144.100.204:9001
echo Hocuspocus:       ws://10.144.100.204:1234
echo.
echo Close console windows to stop services.
```

---

## 7. Standalone Deployment Checklist

- [ ] MinIO binary indirildi (`/opt/minio` veya `C:\minio\`)
- [ ] Data dizini oluşturuldu (`/data/minio` veya `C:\minio-data\`)
- [ ] MinIO started (`http://10.144.100.204:9001` erişilebilir)
- [ ] Buckets oluşturuldu: `report-uploads`, `report-snapshots`
- [ ] Access Key oluşturuldu (minioadmin değil, custom)
- [ ] `.env` dosyasında `MINIO_*` variables set
- [ ] CORS rules configured (frontend origin)
- [ ] FastAPI service STORAGE_USE_LOCAL=false'a set
- [ ] MinIO service restarts on reboot (systemd/NSSM)

---

## 8. Troubleshooting

### MinIO Connection Refused

```bash
# Kontrol et
curl http://10.144.100.204:9000/minio/health/live

# MinIO process'i check et
ps aux | grep minio
# veya (Windows)
tasklist | findstr minio
```

### S3 Upload Fails

```python
# Debug mode
import boto3
boto3.set_stream_logger('boto3.resources', logging.DEBUG)

# Network check
import socket
socket.create_connection(('10.144.100.204', 9000), timeout=5)
```

### Bucket Permission Denied

```bash
# MinIO console'dan policy kontrol et
./mc policy info minio/report-uploads

# Policy set
./mc policy set public minio/report-uploads  # public upload
./mc policy set private minio/report-uploads # private (repl ile)
```

---

## 9. Production Notes

**Recommended:**
- Firewall: S3 API (9000) sadece backend'den accessible
- Web console (9001) sadece admin network'ten
- Backups: nightly MinIO data directory backup
- Capacity: Reports büyüdükçe disk space monitor et
- TLS: Production'da HTTPS/SSL enable et

**Security:**
- Unique access key (not minioadmin:minioadmin)
- Regular key rotation (3-6 ayda bir)
- Audit logging enable
- Encryption at rest (minio_encryption config)
