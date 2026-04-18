# On-Premise Configuration — Veni AI Report Factory (Pivot v3)

Bu dokümüntasyon, CLAUDE.md'de tanımlanan tüm on-premise servislerin proje konfigürasyonuyla entegrasyonunu açıklar.

---

## 1. Servisler ve Network Yapısı

### Development Environment (docker-compose.yaml)

```
localhost:3000    ← Frontend (Next.js)
   ↓
localhost:8000    ← Backend API (FastAPI)
   ↓
postgres:5432     ← PostgreSQL (container içi)
redis:6379        ← Redis (container içi)
   ↓
localhost:8821    ← vLLM (external, shared GPU cluster)
https://jina-embedding.aiops.albarakaturk.local  ← Jina Embedding (external)
localhost:1234    ← Hocuspocus (realtime collab, kurulacak)
```

### Production Environment (On-Premise)

```
10.144.100.204:25432   ← PostgreSQL + pgvector
10.144.100.204:46379   ← Redis
10.144.100.204:8821    ← vLLM (GPU cluster)
10.144.100.204:9000    ← MinIO (object storage)
jina-embedding.aiops.albarakaturk.local  ← Jina Embedding
collab-server:1234     ← Hocuspocus server (Node.js, new)
```

---

## 2. Environment Variables Reference

### Database & pgvector

| Variable | Dev Default | Prod Value | Not |
|---|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@postgres:5432/sustainability` | `postgresql+asyncpg://vector_user1:vector_78s64+w2@10.144.100.204:25432/vectordb1` | Async driver required |
| `DATABASE_ALLOW_LOCAL_DEV` | `true` | `false` (prod'da validation skip edilmez) | |
| `PGVECTOR_HOST` | `postgres` | `10.144.100.204` | |
| `PGVECTOR_PORT` | `5432` | `25432` | |
| `PGVECTOR_USER` | `postgres` | `vector_user1` | |
| `PGVECTOR_PASSWORD` | `postgres` | `vector_78s64+w2` | ⚠️ Secret manager'dan oku, hardcode etme |
| `PGVECTOR_DATABASE` | `sustainability` | `vectordb1` | |
| `PGVECTOR_EMBEDDING_DIMENSION` | `1024` | `1024` | Jina v4 output dimension |

### vLLM (Local LLM)

| Variable | Dev Value | Prod Value | Not |
|---|---|---|---|
| `VLLM_BASE_URL` | `http://localhost:8821/v1` | `http://10.144.100.204:8821/v1` | OpenAI-compatible endpoint |
| `VLLM_API_KEY` | `not-needed` | `not-needed` | Local ortamda key gereksiz |
| `VLLM_MODEL` | `Qwen/Qwen3.6-35B-A3B-FP8` | Aynı | Model override yapılmaz |
| `VLLM_TIMEOUT_SECONDS` | `180` | `180` | vLLM request timeout |
| `LLM_GENERATION_MAX_TOKENS` | `2048` | `2048` | Per-section max output |
| `LLM_GENERATION_TEMPERATURE` | `0.7` | `0.7` | 0.0–2.0 arası |
| `LLM_BATCH_WORKER_TIMEOUT_SECONDS` | `180` | `180` | Batch job timeout |
| `LLM_BATCH_WORKER_RETRY_COUNT` | `3` | `3` | Exponential backoff ile retry |

### Redis (Queue & State)

| Variable | Dev Default | Prod Value | Not |
|---|---|---|---|
| `REDIS_HOST` | `redis` | `10.144.100.204` | |
| `REDIS_PORT` | `6379` | `46379` | Non-standard port |
| `REDIS_PASSWORD` | (empty) | `O*+78sYtsr` | ⚠️ Secret manager'dan oku |
| `REDIS_URL` | `redis://redis:6379/0` | `redis://:O*+78sYtsr@10.144.100.204:46379/0` | Full URL (password included) |
| `ARQ_QUEUE_NAME` | `arq:queue` | `arq:queue` | Job queue namespace |
| `ARQ_WORKER_CONCURRENCY` | `4` | `4–8` | Worker job parallelism |
| `ARQ_JOB_TIMEOUT_SECONDS` | `180` | `180` | Job execution timeout |
| `ARQ_JOB_RETRY_COUNT` | `3` | `3` | Retry attempts |
| `ARQ_JOB_RETRY_BASE_SECONDS` | `5` | `5` | Exponential backoff base |
| `ARQ_JOB_RETRY_MAX_DEFER_SECONDS` | `45` | `45` | Max defer time |

### Jina Embedding (Multimodal)

| Variable | Dev Value | Prod Value | Not |
|---|---|---|---|
| `JINA_EMBEDDING_BASE` | `https://jina-embedding.aiops.albarakaturk.local` | Aynı | Internal corp domain |
| `JINA_EMBEDDING_MODEL` | `jina-embedding-v4` | Aynı | Model version fixed |
| `JINA_TEXT_ENDPOINT` | `/embed/text` | Aynı | Batch & single prompt support |
| `JINA_IMAGE_ENDPOINT` | `/embed/image` | Aynı | Image + query embedding |

### MinIO Storage

| Variable | Dev Value | Prod Value | Not |
|---|---|---|---|
| `STORAGE_USE_LOCAL` | `true` | `false` (prod'da) | Filesystem vs MinIO seçimi |
| `LOCAL_STORAGE_ROOT` | `apps/api/storage` | N/A | Local dev için only |
| `MINIO_ENDPOINT` | `http://minio:9000` | `http://10.144.100.204:9000` | |
| `MINIO_ACCESS_KEY` | `minioadmin` | Var | ⚠️ Secret manager'dan |
| `MINIO_SECRET_KEY` | `minioadmin` | Var | ⚠️ Secret manager'dan |
| `MINIO_USE_SSL` | `false` | `false` (internal) | Cert yönetimi göz önünde tut |
| `MINIO_BUCKET_UPLOADS` | `report-uploads` | Aynı | Excel, image uploads |
| `MINIO_BUCKET_SNAPSHOTS` | `report-snapshots` | Aynı | Published reports |

### Hocuspocus (Realtime Collab)

| Variable | Dev Value | Prod Value | Not |
|---|---|---|---|
| `HOCUSPOCUS_HOST` | `http://localhost:1234` | `http://collab-server:1234` | Container hostname |
| `HOCUSPOCUS_WS_URL` | `ws://localhost:1234` | `wss://collab.internal/` (TLS) | Production'da HTTPS proxy behind |
| `HOCUSPOCUS_JWT_SECRET` | `change-in-production` | Strong secret | ⚠️ Secret manager'dan oku |
| `NEXT_PUBLIC_HOCUSPOCUS_URL` | `ws://127.0.0.1:1234` | Client-facing WS URL | Frontend'de kullanılan |

### Frontend URLs

| Variable | Dev Value | Prod Value | Not |
|---|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `http://127.0.0.1:8000` | `https://api.internal.albarakaturk.local/` | Backend API |
| `NEXT_PUBLIC_APP_BASE_URL` | `http://127.0.0.1:3000` | `https://report.internal.albarakaturk.local/` | Frontend public URL |

### CORS & Security

| Variable | Dev Value | Prod Value | Not |
|---|---|---|---|
| `CORS_ALLOW_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | `https://report.internal.albarakaturk.local/` | Comma-separated list |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | `report.internal.albarakaturk.local` | FastAPI allowed_hosts |

### Report Configuration

| Variable | Default | Not |
|---|---|---|
| `REPORT_TEMPLATE_DEFAULT_VERSION` | `pivot-v3` | Template DB version |
| `REPORT_FACTORY_DEFAULT_LOCALE` | `tr-TR` | Türkçe first, EN secondary |
| `REPORT_MAX_SECTION_LENGTH` | `5000` | Chars per section |
| `REPORT_AUTO_SAVE_INTERVAL_SECONDS` | `60` | Tiptap Y.js snapshot freq |

### Audit & Logging

| Variable | Default | Not |
|---|---|---|
| `LOG_LEVEL` | `INFO` | DEBUG/INFO/WARNING/ERROR |
| `AUDIT_ENABLED` | `true` | AuditEvent tablosu kayıt |
| `AUDIT_RETENTION_DAYS` | `365` | Cleanup policy |

### Health Checks

| Variable | Default | Not |
|---|---|---|
| `HEALTH_CHECK_VLLM_ENABLED` | `true` | /health endpoint checks |
| `HEALTH_CHECK_PGVECTOR_ENABLED` | `true` | Bağlantı test etme |
| `HEALTH_CHECK_REDIS_ENABLED` | `true` | Redis ping |
| `HEALTH_CHECK_JINA_ENABLED` | `true` | Jina embedding availability |
| `HEALTH_CHECK_TIMEOUT_SECONDS` | `5` | Per-service timeout |

---

## 3. Docker Compose — Development Setup

### Start Services

```bash
docker-compose up -d
```

Bu command aşağıdaki containers başlatır:

1. **postgres:16** — PostgreSQL + pgvector extension
2. **redis:7** — In-memory queue & state
3. **api:dev** — FastAPI (FastAPI + Alembic migrations)
4. **worker:dev** — ARQ job worker
5. **web:dev** — Next.js frontend

### Health Check

```bash
# API ready?
curl http://127.0.0.1:8000/health/ready

# PostgreSQL?
docker-compose exec postgres pg_isready -U postgres

# Redis?
docker-compose exec redis redis-cli ping

# Frontend?
curl http://127.0.0.1:3000
```

---

## 4. Production Deployment — Environment Files

### prod.env (Secret manager'dan güvenli şekilde oku)

```env
# Database
DATABASE_URL=postgresql+asyncpg://vector_user1:${PGVECTOR_PASSWORD}@10.144.100.204:25432/vectordb1
PGVECTOR_PASSWORD=${SECRET_PGVECTOR_PASSWORD}

# Redis
REDIS_PASSWORD=${SECRET_REDIS_PASSWORD}
REDIS_URL=redis://:${REDIS_PASSWORD}@10.144.100.204:46379/0

# MinIO
MINIO_ACCESS_KEY=${SECRET_MINIO_ACCESS_KEY}
MINIO_SECRET_KEY=${SECRET_MINIO_SECRET_KEY}

# Hocuspocus
HOCUSPOCUS_JWT_SECRET=${SECRET_HOCUSPOCUS_JWT_SECRET}

# CORS & URLs (prod domains)
NEXT_PUBLIC_API_BASE_URL=https://api.internal.albarakaturk.local
NEXT_PUBLIC_APP_BASE_URL=https://report.internal.albarakaturk.local
HOCUSPOCUS_WS_URL=wss://report.internal.albarakaturk.local/collab
CORS_ALLOW_ORIGINS=https://report.internal.albarakaturk.local

# Storage: prod'da MinIO kullan
STORAGE_USE_LOCAL=false
```

### Secret Manager Integration (örnek: Kubernetes Secrets)

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: veni-ai-secrets
type: Opaque
stringData:
  PGVECTOR_PASSWORD: "vector_78s64+w2"
  REDIS_PASSWORD: "O*+78sYtsr"
  MINIO_ACCESS_KEY: "prod-access-key"
  MINIO_SECRET_KEY: "prod-secret-key"
  HOCUSPOCUS_JWT_SECRET: "prod-jwt-secret-xxx"
```

Pod'da secret'ları enjekte et:

```yaml
containers:
- name: api
  env:
  - name: PGVECTOR_PASSWORD
    valueFrom:
      secretKeyRef:
        name: veni-ai-secrets
        key: PGVECTOR_PASSWORD
  - name: REDIS_PASSWORD
    valueFrom:
      secretKeyRef:
        name: veni-ai-secrets
        key: REDIS_PASSWORD
```

---

## 5. Network & Firewall Rules (On-Premise)

### Allowed Connections

```
API Container → PostgreSQL (10.144.100.204:25432) ✓ TCP
API Container → Redis (10.144.100.204:46379) ✓ TCP
API Container → vLLM (10.144.100.204:8821) ✓ TCP
API Container → Jina (jina-embedding.aiops.albarakaturk.local:443) ✓ HTTPS
Frontend → API (FastAPI) ✓ HTTP/HTTPS
Frontend → Hocuspocus (WebSocket) ✓ WS/WSS
Workers → All of the above ✓
```

### Blocked Connections

```
❌ API/Worker → External internet (no cloud APIs)
❌ Direct browser → PostgreSQL/Redis/vLLM
❌ Unencrypted WebSocket in production (use wss://)
```

---

## 6. Credentials Management

### ⚠️ CRITICAL: Never Hardcode Secrets

**Yapılacak:**
- Environment variables via `.env` (dev only)
- Secret manager (Kubernetes Secrets, Vault, HashiCorp Consul) (prod)
- Docker secrets (Swarm)
- CI/CD secrets (GitHub Actions)

**Yapılmayacak:**
- `.env` prod'ya commit etme
- `settings.py`'de default password
- `compose.yaml`'de credential enjeksiyonu

### Rotation Policy

- PostgreSQL password: 3 ayda bir
- Redis password: 3 ayda bir
- MinIO keys: 6 ayda bir
- JWT secrets: 1 yılda bir (ve deployment'la birlikte)

---

## 7. Health & Monitoring

### API Health Endpoint

```bash
GET /health/ready

Response:
{
  "status": "ready",
  "checks": {
    "vllm": "ok",
    "pgvector": "ok",
    "redis": "ok",
    "jina": "ok"
  }
}
```

### Logs

```bash
# API
docker-compose logs -f api

# Worker
docker-compose logs -f worker

# Redis
docker-compose logs -f redis

# PostgreSQL
docker-compose logs -f postgres
```

### Metrics (Optional, Faz 2'ye ertelendi)

- vLLM: GPU memory, tokens/sec, latency
- PostgreSQL: Active connections, query latency
- Redis: Memory usage, key expiration
- API: Request latency, error rate

---

## 8. Troubleshooting

### vLLM Connection Failed

```
Error: Failed to connect to http://localhost:8821/v1
```

**Çözüm:**
1. `VLLM_BASE_URL` kontrol et
2. vLLM container health check'ini sor: `curl http://localhost:8821/v1/models`
3. Network connectivity: `nc -zv 10.144.100.204 8821`

### PostgreSQL Connection Pool Exhausted

```
Error: FATAL: too many connections
```

**Çözüm:**
1. Connection pool size kontrol et (Alembic, SQLAlchemy)
2. Idle connections kill et: `SELECT pg_terminate_backend(pid) FROM ...`

### Redis Memory Full

```
Error: OOM command not allowed when used memory > maxmemory
```

**Çözüm:**
1. `MAXMEMORY` policy kontrol et (allkeys-lru recommended)
2. Stale jobs cleanup: `ARQ_JOB_TIMEOUT_SECONDS` düşür

### Jina Embedding Timeout

```
Error: Timeout contacting https://jina-embedding.aiops.albarakaturk.local
```

**Çözüm:**
1. Network latency check: `ping jina-embedding.aiops.albarakaturk.local`
2. Firewall rules kontrol et (HTTPS 443 açık mı?)
3. Jina service availability: kendi dashboardını kontrol et

---

## 9. Testing Connectivity

```bash
# PostgreSQL
python -c "
import asyncio
import asyncpg
async def test():
    conn = await asyncpg.connect('postgresql://vector_user1:vector_78s64+w2@10.144.100.204:25432/vectordb1')
    result = await conn.fetchval('SELECT 1')
    print(f'✓ pgvector connected: {result}')
asyncio.run(test())
"

# Redis
python -c "
import redis
r = redis.Redis(host='10.144.100.204', port=46379, password='O*+78sYtsr')
print(f'✓ Redis: {r.ping()}')
"

# vLLM (OpenAI SDK)
python -c "
from openai import AsyncOpenAI
client = AsyncOpenAI(base_url='http://localhost:8821/v1', api_key='not-needed')
# (async call in main())
"

# Jina Embedding
python -c "
import requests
r = requests.post('https://jina-embedding.aiops.albarakaturk.local/embed/text',
    json={'model': 'jina-embedding-v4', 'texts': ['test']})
print(f'✓ Jina: status={r.status_code}')
"
```

---

## 10. Migration from Old Azure Config

### Silinen Environment Variables

- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_CHAT_DEPLOYMENT`
- `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`
- `AZURE_STORAGE_ACCOUNT_NAME`
- `AZURE_STORAGE_CONNECTION_STRING`
- `AZURE_AI_SEARCH_ENDPOINT`
- `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT`

### Settings.py Migrations

Eski code:
```python
from azure.openai import AzureOpenAI
client = AzureOpenAI(
    api_key=settings.azure_openai_api_key,
    api_version=settings.azure_openai_api_version,
    azure_endpoint=settings.azure_openai_endpoint,
)
```

Yeni code:
```python
from openai import AsyncOpenAI
client = AsyncOpenAI(
    base_url=settings.vllm_base_url,
    api_key=settings.vllm_api_key,
)
```

---

## 11. Checklist — Before Go-Live

- [ ] PostgreSQL + pgvector test connectivity
- [ ] Redis connection pool sized correctly
- [ ] vLLM health check passing
- [ ] Jina Embedding accessible (HTTPS, cert valid)
- [ ] MinIO buckets created + CORS rules
- [ ] Secrets secured (not in `.env` files)
- [ ] CORS whitelist configured
- [ ] Firewall rules in place
- [ ] Health endpoint returning 200
- [ ] Sample LLM generation test passed
- [ ] Audit logging enabled
- [ ] Backups scheduled (PostgreSQL daily, MinIO)

---

## 12. References

- CLAUDE.md — Project architecture & rules
- .env.example — All variables with defaults
- apps/api/app/core/settings.py — Pydantic model
- compose.yaml — Local dev configuration
