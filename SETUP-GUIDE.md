# Veni AI Report Factory — Complete Setup Guide

**Status:** ✅ Configuration transformation complete (April 2026)

Bu dokümünt, projeyi **standalone (Docker olmayan) on-premise ortamında** ayağa kaldırmak için gereken tüm adımları içerir.

---

## 📚 Documentation Index

1. **[CLAUDE.md](CLAUDE.md)** — Proje mimarisi, kararlar, roadmap (Türkçe)
2. **[ON-PREMISE-CONFIG.md](ON-PREMISE-CONFIG.md)** — Tüm environment variables referans
3. **[MINIO-STANDALONE-SETUP.md](MINIO-STANDALONE-SETUP.md)** — MinIO kurulum & S3 configuration
4. **[STANDALONE-DEPLOYMENT.md](STANDALONE-DEPLOYMENT.md)** — Tüm servisleri standalone ayağa kaldırma
5. **[CONFIGURATION-SUMMARY.md](CONFIGURATION-SUMMARY.md)** — Migration özeti (Azure → On-Premise)

---

## 🚀 Quick Start (5 minutes)

### Prerequisites
- Python 3.10+, Node.js 18+
- Access to remote services: 10.144.100.204 (PostgreSQL, Redis, vLLM, MinIO)
- ~50GB disk space

### Setup Steps

```bash
# 1. Clone & enter project
cd /workspace
git clone <repo>

# 2. Create Python venv
python3 -m venv venv
source venv/bin/activate
pip install -r apps/api/requirements.txt

# 3. Copy .env template
cp .env.example .env
# Edit .env: set PGVECTOR_PASSWORD, REDIS_PASSWORD, MINIO keys

# 4. Database migrations
cd apps/api
alembic upgrade head
cd ../..

# 5. Start MinIO (if not running)
# See: MINIO-STANDALONE-SETUP.md

# 6. Start services (4 terminals)
# Terminal 1:  cd apps/api && uvicorn app.main:app --host 0.0.0.0 --port 8000
# Terminal 2:  python -m arq services.worker.app.WorkerSettings
# Terminal 3:  cd apps/collab-server && npm install && npm start
# Terminal 4:  pnpm --filter web dev --hostname 0.0.0.0 --port 48000

# Or use automation script
chmod +x start-all.sh && ./start-all.sh
```

**Verify:**
```bash
curl http://10.144.100.204:8000/health/ready
# Expected: {"status": "ready", "checks": {...}}

# Open browser
http://10.144.100.204:48000
```

---

## 🛠️ Component Breakdown

### 1. **MinIO** (S3-compatible Object Storage)

| Item | Value |
|------|-------|
| **Purpose** | Excel uploads, report snapshots, images |
| **Port** | 9000 (API), 9001 (Console) |
| **Setup** | See [MINIO-STANDALONE-SETUP.md](MINIO-STANDALONE-SETUP.md) |
| **Buckets** | `report-uploads`, `report-snapshots` |
| **Config** | `MINIO_ENDPOINT=http://10.144.100.204:9000` |

**Console:** http://10.144.100.204:9001

### 2. **FastAPI Backend** (Report Logic)

| Item | Value |
|------|-------|
| **Purpose** | REST API, report draft management, LLM calls |
| **Port** | 8000 |
| **Start** | `uvicorn app.main:app --host 0.0.0.0 --port 8000` |
| **Requirements** | Python 3.10+, pgvector, Redis, vLLM access |
| **Config** | `apps/api/app/core/settings.py` |

**Health:** http://10.144.100.204:8000/health/ready

### 3. **ARQ Worker** (Background Jobs)

| Item | Value |
|------|-------|
| **Purpose** | LLM batch generation, translations, hallucination checks |
| **Start** | `python -m arq services.worker.app.WorkerSettings` |
| **Queue** | Redis (10.144.100.204:46379) |
| **Config** | `ARQ_QUEUE_NAME=arq:queue`, `ARQ_WORKER_CONCURRENCY=4` |

### 4. **Hocuspocus Server** (Realtime Collaboration)

| Item | Value |
|------|-------|
| **Purpose** | Live collaborative editing (Y.js + WebSocket) |
| **Port** | 1234 (WebSocket) |
| **Start** | `cd apps/collab-server && npm start` |
| **Framework** | Node.js + Hocuspocus |
| **Config** | `HOCUSPOCUS_JWT_SECRET=...` |

**WebSocket:** ws://10.144.100.204:1234

### 5. **Next.js Frontend** (UI)

| Item | Value |
|------|-------|
| **Purpose** | Web UI for report editing, metrics, collaboration |
| **Port** | 48000 |
| **Start** | `pnpm --filter web dev --hostname 0.0.0.0 --port 48000` |
| **Framework** | Next.js 16 + React 19 + Tiptap |
| **Config** | `NEXT_PUBLIC_API_BASE_URL`, etc. |

**App:** http://10.144.100.204:48000

### 6. **External Services** (Already Running)

| Service | Endpoint | Purpose |
|---------|----------|---------|
| **PostgreSQL + pgvector** | 10.144.100.204:25432 | Report data, vector embeddings |
| **Redis** | 10.144.100.204:46379 | Job queue, session state |
| **vLLM** | 10.144.100.204:8821 | LLM inference (Qwen 3.6-35B) |
| **Jina Embedding** | internal domain:443 | Text & image embeddings |

---

## 📋 Configuration Files

### `.env.example` → `.env` (Development)

```env
DATABASE_URL=postgresql+asyncpg://vector_user1:PASSWORD@10.144.100.204:25432/vectordb1
REDIS_URL=redis://:PASSWORD@10.144.100.204:46379/0
VLLM_BASE_URL=http://10.144.100.204:8821/v1
MINIO_ENDPOINT=http://10.144.100.204:9000
MINIO_ACCESS_KEY=your-key
MINIO_SECRET_KEY=your-secret
NEXT_PUBLIC_API_BASE_URL=http://10.144.100.204:8000
NEXT_PUBLIC_APP_BASE_URL=http://10.144.100.204:48000
NEXT_PUBLIC_HOCUSPOCUS_URL=ws://10.144.100.204:1234
```

**See:** [ON-PREMISE-CONFIG.md § 2](ON-PREMISE-CONFIG.md#2-environment-variables-reference) for all variables.

### `.env.prod.example` (Production)

Same as above, but with:
- Secret manager placeholders: `${SECRET_PGVECTOR_PASSWORD}`, etc.
- TLS URLs: `wss://` instead of `ws://`
- Prod domains: `https://api.internal/`, etc.

---

## 🔐 Credentials

### Required Access Keys

| Service | Credential | Source | Usage |
|---------|-----------|--------|-------|
| **PostgreSQL** | vector_user1 : PASSWORD | DBA / Vault | apps/api, worker |
| **Redis** | PASSWORD | DBA / Vault | apps/api, worker, collab-server |
| **MinIO** | ACCESS_KEY : SECRET_KEY | MinIO console | apps/api storage service |
| **JWT Secret** | Random string | Generate | hocuspocus-server only |

### Security Policy

- ✅ **DO:** Environment variables (dev), Secret Manager (prod)
- ❌ **DON'T:** Hardcode in code, commit `.env.prod` files

---

## ✅ Startup Checklist

### Before Running

- [ ] Python 3.10+ installed
- [ ] Node.js 18+ installed
- [ ] Virtual environment created
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file configured with credentials
- [ ] Network access to 10.144.100.204 confirmed
- [ ] MinIO running & buckets created
- [ ] Database migrations applied

### Startup Sequence

1. **MinIO** (if standalone): `/opt/minio server /data/minio --console-address :9001`
2. **FastAPI**: `uvicorn app.main:app --host 0.0.0.0 --port 8000` (wait for "ready")
3. **Worker**: `python -m arq services.worker.app.WorkerSettings`
4. **Hocuspocus**: `npm start` (from apps/collab-server)
5. **Frontend**: `pnpm --filter web dev --hostname 0.0.0.0 --port 48000`

### Verify All Services

```bash
curl http://10.144.100.204:8000/health/ready
curl http://10.144.100.204:48000
curl http://10.144.100.204:9001  # MinIO console
# WebSocket test (browser console):
#   ws = new WebSocket("ws://10.144.100.204:1234")
```

---

## 🚨 Troubleshooting

| Issue | Solution |
|-------|----------|
| Port already in use | `lsof -i :8000` → `kill -9 <PID>` or use different port |
| Module not found | Ensure venv activated: `source venv/bin/activate` |
| Database connection failed | Check `.env` `DATABASE_URL`, network access |
| MinIO connection refused | Check endpoint IP:port, firewall rules |
| Redis auth failed | Verify `REDIS_PASSWORD` in `.env` |
| LLM timeout | Check vLLM service health: `curl http://10.144.100.204:8821/v1/models` |

**Detailed troubleshooting:** See [STANDALONE-DEPLOYMENT.md § 11](STANDALONE-DEPLOYMENT.md#11-troubleshooting)

---

## 📖 Next Steps

1. **Follow [MINIO-STANDALONE-SETUP.md](MINIO-STANDALONE-SETUP.md)**
   - Download & start MinIO binary
   - Create buckets & access keys

2. **Follow [STANDALONE-DEPLOYMENT.md](STANDALONE-DEPLOYMENT.md)**
   - Create Python venv
   - Setup `.env` file
   - Start all services

3. **Test & Verify**
   - Open http://10.144.100.204:48000 in browser
   - Create sample report
   - Test LLM generation
   - Verify file uploads to MinIO

4. **Production Deployment** (Later)
   - Setup systemd services (Linux)
   - Configure TLS/HTTPS
   - Use Secret Manager for credentials
   - Setup monitoring & backups

---

## 📞 Support

- **Architecture questions:** See [CLAUDE.md](CLAUDE.md)
- **Environment setup:** See [ON-PREMISE-CONFIG.md](ON-PREMISE-CONFIG.md)
- **MinIO issues:** See [MINIO-STANDALONE-SETUP.md](MINIO-STANDALONE-SETUP.md)
- **Service startup:** See [STANDALONE-DEPLOYMENT.md](STANDALONE-DEPLOYMENT.md)

---

## 🔄 Updated Configuration

**From:** Azure cloud (OpenAI, Storage, Document Intelligence, AI Search)  
**To:** On-Premise (vLLM, pgvector, MinIO, Jina)  
**Benefit:** Air-gapped, offline-capable, vendor-agnostic

**Key Changes:**
- LLM: Azure OpenAI → vLLM (local GPU cluster)
- Vector DB: Azure AI Search → PostgreSQL + pgvector
- Storage: Azure Blob → MinIO
- Embeddings: Azure OpenAI → Jina v4 (multimodal)
- OCR: Azure Document Intelligence → Removed (Q&A input only)

See [CONFIGURATION-SUMMARY.md](CONFIGURATION-SUMMARY.md) for detailed migration.

---

**Last Updated:** April 18, 2026  
**Version:** Pivot v3 (On-Premise)
