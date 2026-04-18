# Standalone Deployment — Veni AI Report Factory

Bu rehber, **Docker olmadan** tüm uygulamayı standalone binary'ler ve native process'ler ile ayağa kaldırmayı açıklar.

---

## 1. Architecture — Services & Ports

```
┌─────────────────────────────────────────────────────────────┐
│                   Veni AI Standalone Setup                   │
└─────────────────────────────────────────────────────────────┘

┌─ Frontend (Next.js) ──────────────────────────────────────┐
│ Port: 48000                                               │
│ URL:  http://10.144.100.204:48000                        │
│ Start: pnpm --filter web dev --hostname 0.0.0.0 --port 48000
└──────────────────────────────────────────────────────────┘
           ↓ API calls (HTTP)
┌─ Backend API (FastAPI) ──────────────────────────────────┐
│ Port: 8000                                               │
│ URL:  http://10.144.100.204:8000                        │
│ Start: uvicorn app.main:app --host 0.0.0.0 --port 8000
└──────────────────────────────────────────────────────────┘
           ↓ Queue jobs (Redis)
┌─ Worker (ARQ) ───────────────────────────────────────────┐
│ Port: (background, no HTTP)                             │
│ Start: python -m arq services.worker.app.WorkerSettings
└──────────────────────────────────────────────────────────┘

┌─ Hocuspocus (Node.js) ────────────────────────────────────┐
│ Port: 1234 (WebSocket)                                  │
│ URL:  ws://10.144.100.204:1234                         │
│ Start: npm start (from apps/collab-server)
└──────────────────────────────────────────────────────────┘

┌─ MinIO (S3 Storage) ──────────────────────────────────────┐
│ Port: 9000 (API), 9001 (Console)                       │
│ URL:  http://10.144.100.204:9000 (API)                │
│ URL:  http://10.144.100.204:9001 (Admin)              │
│ Start: /opt/minio server /data/minio --console-address :9001
└──────────────────────────────────────────────────────────┘

┌─ External Services (Remote 10.144.100.204) ─────────────┐
│ PostgreSQL + pgvector: 25432 ✓ (already running)       │
│ Redis:                 46379 ✓ (already running)        │
│ vLLM:                  8821  ✓ (GPU cluster)           │
│ Jina Embedding:        443   ✓ (internal domain)       │
└──────────────────────────────────────────────────────────┘
```

---

## 2. Prerequisites

### System Requirements

- **OS:** Linux, macOS, or Windows
- **Python:** 3.10+
- **Node.js:** 18+ (for Hocuspocus)
- **Disk:** 50GB+ (for data, MinIO buckets)
- **RAM:** 16GB+ recommended
- **Network:** Access to 10.144.100.204 (pgvector, Redis, vLLM, MinIO)

### Network Connectivity Check

```bash
# PostgreSQL
nc -zv 10.144.100.204 25432

# Redis
nc -zv 10.144.100.204 46379

# vLLM
curl -s http://10.144.100.204:8821/v1/models

# Jina Embedding
curl -s https://jina-embedding.aiops.albarakaturk.local/status

# MinIO
curl -s http://10.144.100.204:9000/minio/health/live
```

---

## 3. Step 1: Setup Python Environment

### Create Virtual Environment

**Linux/macOS:**
```bash
cd /workspace  # or your project root
python3 -m venv venv
source venv/bin/activate
```

**Windows (PowerShell):**
```powershell
cd C:\workspace
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Install Dependencies

```bash
# Backend dependencies
cd apps/api
pip install -r requirements.txt
cd ../..

# Worker dependencies
pip install arq redis asyncpg pydantic

# Frontend dependencies
npm install -g pnpm  # if not installed
pnpm install
```

---

## 4. Step 2: Setup MinIO

**详见:** [MINIO-STANDALONE-SETUP.md](MINIO-STANDALONE-SETUP.md)

Quick start:

```bash
# 1. Download MinIO binary
wget https://dl.min.io/server/minio/release/linux-amd64/minio -O /opt/minio
chmod +x /opt/minio

# 2. Create data directory
mkdir -p /data/minio
chmod 700 /data/minio

# 3. Start MinIO
/opt/minio server /data/minio --console-address :9001

# 4. Console: http://10.144.100.204:9001
# Create buckets: report-uploads, report-snapshots
# Create access key (not minioadmin:minioadmin)
```

---

## 5. Step 3: Setup Database Migrations

```bash
cd apps/api

# Ensure connection to pgvector
export DATABASE_URL=postgresql+asyncpg://vector_user1:PASSWORD@10.144.100.204:25432/vectordb1

# Run migrations
alembic upgrade head
```

---

## 6. Step 4: Setup Environment File

Create `.env` file in project root:

```env
# ========== Core ==========
APP_ENV=development
REPORT_FACTORY_DEFAULT_LOCALE=tr-TR

# ========== Database & Vector ==========
DATABASE_URL=postgresql+asyncpg://vector_user1:PASSWORD@10.144.100.204:25432/vectordb1
DATABASE_ALLOW_LOCAL_DEV=true
PGVECTOR_HOST=10.144.100.204
PGVECTOR_PORT=25432
PGVECTOR_USER=vector_user1
PGVECTOR_PASSWORD=PASSWORD
PGVECTOR_DATABASE=vectordb1
PGVECTOR_EMBEDDING_DIMENSION=1024

# ========== vLLM ==========
VLLM_BASE_URL=http://10.144.100.204:8821/v1
VLLM_API_KEY=not-needed
VLLM_TIMEOUT_SECONDS=180
LLM_GENERATION_MAX_TOKENS=2048
LLM_GENERATION_TEMPERATURE=0.7

# ========== Redis ==========
REDIS_HOST=10.144.100.204
REDIS_PORT=46379
REDIS_PASSWORD=PASSWORD
REDIS_URL=redis://:PASSWORD@10.144.100.204:46379/0
ARQ_QUEUE_NAME=arq:queue
ARQ_WORKER_CONCURRENCY=4

# ========== Jina Embedding ==========
JINA_EMBEDDING_BASE=https://jina-embedding.aiops.albarakaturk.local
JINA_EMBEDDING_MODEL=jina-embedding-v4

# ========== MinIO ==========
STORAGE_USE_LOCAL=false
MINIO_ENDPOINT=http://10.144.100.204:9000
MINIO_ACCESS_KEY=your-access-key
MINIO_SECRET_KEY=your-secret-key
MINIO_USE_SSL=false
MINIO_BUCKET_UPLOADS=report-uploads
MINIO_BUCKET_SNAPSHOTS=report-snapshots

# ========== Hocuspocus ==========
HOCUSPOCUS_HOST=http://localhost:1234
HOCUSPOCUS_WS_URL=ws://10.144.100.204:1234
HOCUSPOCUS_JWT_SECRET=dev-secret-change-in-prod

# ========== Frontend URLs ==========
NEXT_PUBLIC_API_BASE_URL=http://10.144.100.204:8000
NEXT_PUBLIC_APP_BASE_URL=http://10.144.100.204:48000
NEXT_PUBLIC_HOCUSPOCUS_URL=ws://10.144.100.204:1234

# ========== CORS ==========
CORS_ALLOW_ORIGINS=http://10.144.100.204:48000,http://localhost:48000
ALLOWED_HOSTS=10.144.100.204,localhost

# ========== Logging & Audit ==========
LOG_LEVEL=INFO
AUDIT_ENABLED=true
```

---

## 7. Step 5: Start Services (Manual)

### Terminal 1: FastAPI Backend

```bash
cd apps/api
source ../venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

Test:
```bash
curl http://10.144.100.204:8000/health/ready
# {"status": "ready", "checks": {...}}
```

### Terminal 2: ARQ Worker

```bash
source venv/bin/activate
python -m arq services.worker.app.WorkerSettings
```

Output:
```
starting worker pool (con=1 que=1)
pool job from queue default
```

### Terminal 3: Hocuspocus Server

```bash
cd apps/collab-server
npm install
npm start
```

Output:
```
Server listening on port 1234
```

### Terminal 4: Next.js Frontend

```bash
export NEXT_PUBLIC_API_BASE_URL=http://10.144.100.204:8000
export NEXT_PUBLIC_APP_BASE_URL=http://10.144.100.204:48000
export NEXT_PUBLIC_HOCUSPOCUS_URL=ws://10.144.100.204:1234

pnpm --filter web dev --hostname 0.0.0.0 --port 48000
```

Output:
```
▲ Next.js 16
  ready - started server on 0.0.0.0:48000
```

---

## 8. Step 6: Automated Startup Scripts

### start-all.sh (Linux/macOS)

```bash
#!/bin/bash
set -e

WORKSPACE=/workspace
export PYTHONUNBUFFERED=1

# Load .env
export $(cat $WORKSPACE/.env | xargs)

# MinIO (if local)
if [ "$MINIO_ENDPOINT" = "http://localhost:9000" ]; then
  echo "▶ Starting MinIO..."
  /opt/minio server /data/minio --console-address :9001 > /tmp/minio.log 2>&1 &
  echo $! > /tmp/minio.pid
  sleep 2
fi

# FastAPI
echo "▶ Starting FastAPI..."
cd $WORKSPACE/apps/api
source $WORKSPACE/venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/api.log 2>&1 &
echo $! > /tmp/api.pid
sleep 3

# Worker
echo "▶ Starting Worker..."
source $WORKSPACE/venv/bin/activate
python -m arq services.worker.app.WorkerSettings > /tmp/worker.log 2>&1 &
echo $! > /tmp/worker.pid

# Hocuspocus
echo "▶ Starting Hocuspocus..."
cd $WORKSPACE/apps/collab-server
npm start > /tmp/hocuspocus.log 2>&1 &
echo $! > /tmp/hocuspocus.pid
sleep 2

# Frontend
echo "▶ Starting Frontend..."
cd $WORKSPACE
pnpm --filter web dev --hostname 0.0.0.0 --port 48000 > /tmp/web.log 2>&1 &
echo $! > /tmp/web.pid

echo ""
echo "✅ All services started!"
echo ""
echo "API:        http://10.144.100.204:8000"
echo "Frontend:   http://10.144.100.204:48000"
echo "Hocuspocus: ws://10.144.100.204:1234"
echo ""
echo "Logs:"
echo "  API:        tail -f /tmp/api.log"
echo "  Worker:     tail -f /tmp/worker.log"
echo "  Hocuspocus: tail -f /tmp/hocuspocus.log"
echo "  Frontend:   tail -f /tmp/web.log"
```

**Usage:**
```bash
chmod +x start-all.sh
./start-all.sh
```

### stop-all.sh (Linux/macOS)

```bash
#!/bin/bash

for pidfile in /tmp/minio.pid /tmp/api.pid /tmp/worker.pid /tmp/hocuspocus.pid /tmp/web.pid; do
  if [ -f $pidfile ]; then
    pid=$(cat $pidfile)
    kill $pid 2>/dev/null || true
    rm $pidfile
  fi
done

echo "✓ All services stopped"
```

---

## 9. Systemd Services (Linux Production)

### /etc/systemd/system/veni-api.service

```ini
[Unit]
Description=Veni AI Report Factory - FastAPI
After=network.target

[Service]
Type=simple
User=veni
WorkingDirectory=/workspace/apps/api
EnvironmentFile=/workspace/.env
ExecStart=/workspace/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### /etc/systemd/system/veni-worker.service

```ini
[Unit]
Description=Veni AI Report Factory - ARQ Worker
After=network.target

[Service]
Type=simple
User=veni
WorkingDirectory=/workspace
EnvironmentFile=/workspace/.env
ExecStart=/workspace/venv/bin/python -m arq services.worker.app.WorkerSettings
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### /etc/systemd/system/veni-hocuspocus.service

```ini
[Unit]
Description=Veni AI Report Factory - Hocuspocus
After=network.target

[Service]
Type=simple
User=veni
WorkingDirectory=/workspace/apps/collab-server
ExecStart=/usr/bin/npm start
Restart=always
RestartSec=5
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"

[Install]
WantedBy=multi-user.target
```

### /etc/systemd/system/veni-web.service

```ini
[Unit]
Description=Veni AI Report Factory - Frontend
After=network.target

[Service]
Type=simple
User=veni
WorkingDirectory=/workspace
EnvironmentFile=/workspace/.env
ExecStart=/usr/local/bin/pnpm --filter web dev --hostname 0.0.0.0 --port 48000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**Enable & start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable veni-api veni-worker veni-hocuspocus veni-web
sudo systemctl start veni-api veni-worker veni-hocuspocus veni-web
sudo systemctl status veni-api veni-worker veni-hocuspocus veni-web
```

---

## 10. Monitoring & Logs

### Log Files

```bash
# API
tail -f /tmp/api.log
# or (systemd)
journalctl -u veni-api -f

# Worker
tail -f /tmp/worker.log
journalctl -u veni-worker -f

# Hocuspocus
tail -f /tmp/hocuspocus.log
journalctl -u veni-hocuspocus -f

# Frontend
tail -f /tmp/web.log
journalctl -u veni-web -f
```

### Health Check Script

```bash
#!/bin/bash

echo "Checking Veni AI services..."
echo ""

# API
if curl -s http://10.144.100.204:8000/health/ready > /dev/null; then
  echo "✓ API: OK"
else
  echo "✗ API: FAILED"
fi

# Frontend
if curl -s http://10.144.100.204:48000 > /dev/null; then
  echo "✓ Frontend: OK"
else
  echo "✗ Frontend: FAILED"
fi

# MinIO
if curl -s http://10.144.100.204:9000/minio/health/live > /dev/null; then
  echo "✓ MinIO: OK"
else
  echo "✗ MinIO: FAILED"
fi

# PostgreSQL
if python3 -c "import asyncpg; import asyncio; asyncio.run(asyncpg.connect('postgresql://vector_user1:PASSWORD@10.144.100.204:25432/vectordb1'))" 2>/dev/null; then
  echo "✓ PostgreSQL: OK"
else
  echo "✗ PostgreSQL: FAILED"
fi

# Redis
if redis-cli -h 10.144.100.204 -p 46379 ping > /dev/null 2>&1; then
  echo "✓ Redis: OK"
else
  echo "✗ Redis: FAILED"
fi

# vLLM
if curl -s http://10.144.100.204:8821/v1/models > /dev/null; then
  echo "✓ vLLM: OK"
else
  echo "✗ vLLM: FAILED"
fi

echo ""
```

---

## 11. Troubleshooting

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000
# Kill it
kill -9 <PID>

# Or use different port
uvicorn app.main:app --port 8001
```

### Python Module Not Found

```bash
# Ensure venv activated
source venv/bin/activate

# Check pip install
pip list | grep package-name

# Install missing
pip install -r requirements.txt
```

### Database Connection Failed

```python
# Test connection
python3 << 'EOF'
import asyncpg
import asyncio

async def test():
    conn = await asyncpg.connect(
        'postgresql://vector_user1:PASSWORD@10.144.100.204:25432/vectordb1'
    )
    result = await conn.fetchval('SELECT 1')
    print(f"Connected: {result}")

asyncio.run(test())
EOF
```

### Redis Connection Refused

```bash
# Check Redis
redis-cli -h 10.144.100.204 -p 46379 -a PASSWORD ping

# Check firewall
nc -zv 10.144.100.204 46379
```

---

## 12. Checklist

- [ ] Virtual environment created & activated
- [ ] Dependencies installed (apps/api, services/worker)
- [ ] MinIO binary downloaded & data directory created
- [ ] MinIO buckets created: report-uploads, report-snapshots
- [ ] .env file created with correct credentials
- [ ] Database migrations run (alembic upgrade head)
- [ ] Network connectivity verified to remote services
- [ ] API health endpoint responding
- [ ] Worker starting without errors
- [ ] Hocuspocus server listening on port 1234
- [ ] Frontend accessible at http://10.144.100.204:48000
- [ ] Sample report generation tested
- [ ] MinIO console reachable at http://10.144.100.204:9001

---

## 13. Quick Reference

| Service | Port | Start Command | Health Check |
|---------|------|---------------|--------------|
| API | 8000 | `uvicorn app.main:app --host 0.0.0.0 --port 8000` | `curl http://10.144.100.204:8000/health/ready` |
| Frontend | 48000 | `pnpm --filter web dev --hostname 0.0.0.0 --port 48000` | `curl http://10.144.100.204:48000` |
| Hocuspocus | 1234 | `npm start` (from apps/collab-server) | WebSocket test |
| Worker | (bg) | `python -m arq services.worker.app.WorkerSettings` | Check logs |
| MinIO | 9000 / 9001 | `/opt/minio server /data/minio --console-address :9001` | `curl http://10.144.100.204:9001` |

---

**Next:** See [MINIO-STANDALONE-SETUP.md](MINIO-STANDALONE-SETUP.md) for detailed MinIO configuration.
