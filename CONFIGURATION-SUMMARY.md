# Configuration Transformation Summary — On-Premise Pivot (v3)

## Overview

Proje eski Azure/ERP-odaklı bulut konfigürasyonundan **on-premise, air-gapped, LLM-native** ortama dönüştürüldü. Tüm environment variables, settings, ve deployment konfigürasyonları güncellenmiştir.

---

## Files Modified

### 1. `.env.example` (Completely Rewritten)

**Eski yapı:** Azure OpenAI, Azure Storage, Azure Document Intelligence, Azure AI Search

**Yeni yapı:** vLLM, pgvector, Redis, Jina Embedding, MinIO

**Key additions:**
```env
# vLLM (Local LLM)
VLLM_BASE_URL=http://localhost:8821/v1
VLLM_MODEL=Qwen/Qwen3.6-35B-A3B-FP8

# pgvector (Vector DB + Regular PostgreSQL)
PGVECTOR_HOST=10.144.100.204
PGVECTOR_EMBEDDING_DIMENSION=1024

# Redis (Queue + State)
REDIS_HOST=10.144.100.204
REDIS_PORT=46379

# Jina Embedding (Multimodal)
JINA_EMBEDDING_BASE=https://jina-embedding.aiops.albarakaturk.local

# MinIO (Storage)
MINIO_ENDPOINT=http://10.144.100.204:9000

# Hocuspocus (Realtime Collab)
HOCUSPOCUS_WS_URL=ws://localhost:1234
```

### 2. `apps/api/app/core/settings.py` (Major Rewrite)

**Eski Settings class:**
- `allowed_chat_model`, `allowed_embedding_model`, `allowed_image_models` (Azure model names)
- `azure_openai_*`, `azure_storage_*`, `azure_document_intelligence_*`, `azure_ai_search_*` (Azure-specific)
- `workflow_retry_*`, `verifier_mode`, `verifier_pass_threshold` (Legacy workflow fields)
- `connector_operations_inline_fallback`, `connector_agent_stale_after_seconds` (Connector-specific)

**Yeni Settings class:**
- `vllm_base_url`, `vllm_model`, `vllm_timeout_seconds` (vLLM config)
- `pgvector_host`, `pgvector_port`, `pgvector_user`, `pgvector_password`, `pgvector_database`, `pgvector_embedding_dimension` (pgvector)
- `redis_host`, `redis_port`, `redis_password`, `redis_url` (Redis)
- `arq_worker_concurrency`, `arq_job_timeout_seconds`, `arq_job_retry_count` (ARQ job queue)
- `jina_embedding_base`, `jina_embedding_model`, `jina_text_endpoint`, `jina_image_endpoint` (Jina embedding)
- `storage_use_local`, `local_storage_root`, `minio_*` (MinIO vs local FS)
- `hocuspocus_host`, `hocuspocus_ws_url`, `hocuspocus_jwt_secret` (Realtime collab)
- `llm_generation_max_tokens`, `llm_generation_temperature` (LLM generation rules)
- `health_check_*_enabled` (Health check flags)
- `audit_enabled`, `audit_retention_days`, `log_level` (Audit & logging)

**Validator değişiklikler:**
- Eski: `enforce_locked_ai_and_database_policy()` → Azure model validation
- Yeni: `validate_on_premise_configuration()` → PostgreSQL, temperature range, locale checks

### 3. `compose.yaml` (Docker Compose Updated)

**Eski x-backend-shared-env:**
```yaml
AZURE_OPENAI_ENDPOINT: ${AZURE_OPENAI_ENDPOINT:-}
AZURE_OPENAI_API_KEY: ${AZURE_OPENAI_API_KEY:-}
AZURE_OPENAI_CHAT_DEPLOYMENT: ${AZURE_OPENAI_CHAT_DEPLOYMENT:-gpt-5.2}
```

**Yeni x-backend-shared-env:**
```yaml
VLLM_BASE_URL: ${VLLM_BASE_URL:-http://localhost:8821/v1}
VLLM_MODEL: Qwen/Qwen3.6-35B-A3B-FP8
PGVECTOR_HOST: ${PGVECTOR_HOST:-postgres}
PGVECTOR_EMBEDDING_DIMENSION: ${PGVECTOR_EMBEDDING_DIMENSION:-1024}
JINA_EMBEDDING_BASE: ${JINA_EMBEDDING_BASE:-https://jina-embedding.aiops.albarakaturk.local}
REDIS_HOST: ${REDIS_HOST:-redis}
HOCUSPOCUS_WS_URL: ${HOCUSPOCUS_WS_URL:-ws://localhost:1234}
STORAGE_USE_LOCAL: ${STORAGE_USE_LOCAL:-true}
```

**API service changes:**
- Kaldırılan: 30+ Azure variables (storage, document intelligence, AI search, etc.)
- Eklenen: vLLM, pgvector, Redis, Jina, MinIO, Hocuspocus, ARQ, LLM generation, audit, health check variables

**Worker service changes:**
- Kaldırılan: OCR/INDEX/PACKAGE specific retry settings
- Eklenen: LLM batch worker settings, ARQ job settings

**Web service changes:**
- Eklenen: `NEXT_PUBLIC_HOCUSPOCUS_URL` for realtime collab

### 4. New Files Created

#### `ON-PREMISE-CONFIG.md` (Comprehensive Guide)
- Servis mimarisi ve network diagram
- Tüm environment variables referans tablosu
- Development vs Production konfigürasyonu
- Docker compose quick start
- Secret manager integration (Kubernetes example)
- Network & firewall rules
- Health & monitoring
- Troubleshooting
- Test connectivity scripts
- Migration checklist

#### `.env.prod.example`
- Production ortamı için template
- Secret manager placeholder'ları (`${SECRET_*}`)
- Prod-specific values (remote host IPs, wss://, etc.)

#### `CONFIGURATION-SUMMARY.md` (This File)
- Değişiklik özeti
- Migration path
- Key differences table

---

## Configuration Mapping Table

| Aspect | Old (Azure) | New (On-Premise) | Status |
|--------|------------|------------------|--------|
| **Chat LLM** | Azure OpenAI (GPT-4.5) | vLLM (Qwen 3.6 35B) | Migrated |
| **Embeddings** | Azure OpenAI (text-embedding-3) | Jina Embedding v4 | Migrated |
| **Vector DB** | Azure AI Search (cloud) | PostgreSQL + pgvector (on-prem) | Migrated |
| **Cache/Queue** | Redis (local container) | Redis (10.144.100.204:46379) | Upgraded |
| **Storage** | Azure Blob Storage | MinIO (10.144.100.204:9000) | Migrated |
| **OCR** | Azure Document Intelligence | Removed (not needed) | Removed ✓ |
| **Database** | PostgreSQL (Neon cloud) | PostgreSQL (10.144.100.204:25432) | Migrated |
| **Realtime Collab** | Not implemented | Hocuspocus + Y.js | New |
| **Job Queue** | ARQ (local container) | ARQ + Redis (prod cluster) | Same pattern |
| **Internet Access** | Required (cloud APIs) | None (air-gapped) | Secured ✓ |

---

## Environment Variables: Removed vs Added

### ❌ Removed (Legacy Azure)

```
AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_API_KEY
AZURE_OPENAI_API_VERSION
AZURE_OPENAI_CHAT_DEPLOYMENT
AZURE_OPENAI_EMBEDDING_DEPLOYMENT
AZURE_OPENAI_IMAGE_DEPLOYMENT
AZURE_OPENAI_IMAGE_FALLBACK_DEPLOYMENT
AZURE_STORAGE_ACCOUNT_NAME
AZURE_STORAGE_CONNECTION_STRING
AZURE_STORAGE_CONTAINER_RAW
AZURE_STORAGE_CONTAINER_PARSED
AZURE_STORAGE_CONTAINER_ARTIFACTS
AZURE_STORAGE_USE_LOCAL
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT
AZURE_DOCUMENT_INTELLIGENCE_API_KEY
AZURE_DOCUMENT_INTELLIGENCE_API_VERSION
AZURE_AI_SEARCH_ENDPOINT
AZURE_AI_SEARCH_API_KEY
AZURE_AI_SEARCH_INDEX_NAME
AZURE_AI_SEARCH_USE_LOCAL
WORKFLOW_RETRY_MAX_PER_NODE
WORKFLOW_RETRY_BASE_SECONDS
WORKFLOW_RETRY_MAX_DEFER_SECONDS
WORKFLOW_EXECUTE_MAX_STEPS
VERIFIER_MODE
VERIFIER_PASS_THRESHOLD
VERIFIER_UNSURE_THRESHOLD
OCR_JOB_MAX_RETRIES
INDEX_JOB_MAX_RETRIES
PACKAGE_JOB_MAX_RETRIES
CONNECTOR_*
```

### ✅ Added (On-Premise Infrastructure)

**vLLM:**
```
VLLM_BASE_URL
VLLM_API_KEY
VLLM_TIMEOUT_SECONDS
LLM_GENERATION_MAX_TOKENS
LLM_GENERATION_TEMPERATURE
LLM_BATCH_WORKER_TIMEOUT_SECONDS
LLM_BATCH_WORKER_RETRY_COUNT
LLM_BATCH_WORKER_RETRY_BASE_SECONDS
```

**pgvector:**
```
PGVECTOR_HOST
PGVECTOR_PORT
PGVECTOR_USER
PGVECTOR_PASSWORD
PGVECTOR_DATABASE
PGVECTOR_EMBEDDING_DIMENSION
```

**Redis (Enhanced):**
```
REDIS_HOST
REDIS_PORT
REDIS_PASSWORD
ARQ_WORKER_CONCURRENCY
ARQ_JOB_TIMEOUT_SECONDS
ARQ_JOB_RETRY_COUNT
ARQ_JOB_RETRY_BASE_SECONDS
ARQ_JOB_RETRY_MAX_DEFER_SECONDS
```

**Jina Embedding:**
```
JINA_EMBEDDING_BASE
JINA_EMBEDDING_MODEL
JINA_TEXT_ENDPOINT
JINA_IMAGE_ENDPOINT
```

**MinIO:**
```
STORAGE_USE_LOCAL
LOCAL_STORAGE_ROOT
MINIO_ENDPOINT
MINIO_ACCESS_KEY
MINIO_SECRET_KEY
MINIO_USE_SSL
MINIO_BUCKET_UPLOADS
MINIO_BUCKET_SNAPSHOTS
```

**Hocuspocus:**
```
HOCUSPOCUS_HOST
HOCUSPOCUS_WS_URL
HOCUSPOCUS_JWT_SECRET
NEXT_PUBLIC_HOCUSPOCUS_URL
```

**Frontend URLs (New Public URLs):**
```
NEXT_PUBLIC_API_BASE_URL
NEXT_PUBLIC_APP_BASE_URL
NEXT_PUBLIC_HOCUSPOCUS_URL
```

**Audit & Logging:**
```
LOG_LEVEL
AUDIT_ENABLED
AUDIT_RETENTION_DAYS
```

**Health Checks:**
```
HEALTH_CHECK_VLLM_ENABLED
HEALTH_CHECK_PGVECTOR_ENABLED
HEALTH_CHECK_REDIS_ENABLED
HEALTH_CHECK_JINA_ENABLED
HEALTH_CHECK_TIMEOUT_SECONDS
```

---

## Development vs Production Defaults

### Dev (localhost, containers)

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/sustainability
VLLM_BASE_URL=http://localhost:8821/v1
REDIS_URL=redis://redis:6379/0
JINA_EMBEDDING_BASE=https://jina-embedding.aiops.albarakaturk.local (external)
MINIO_ENDPOINT=http://minio:9000 (optional, use local FS)
HOCUSPOCUS_WS_URL=ws://localhost:1234
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_APP_BASE_URL=http://127.0.0.1:3000
STORAGE_USE_LOCAL=true
```

### Prod (10.144.100.204 cluster, internal)

```env
DATABASE_URL=postgresql+asyncpg://vector_user1:${PGVECTOR_PASSWORD}@10.144.100.204:25432/vectordb1
VLLM_BASE_URL=http://10.144.100.204:8821/v1
REDIS_URL=redis://:${SECRET_REDIS_PASSWORD}@10.144.100.204:46379/0
JINA_EMBEDDING_BASE=https://jina-embedding.aiops.albarakaturk.local
MINIO_ENDPOINT=http://10.144.100.204:9000
HOCUSPOCUS_WS_URL=wss://report.internal.albarakaturk.local/collab (TLS)
NEXT_PUBLIC_API_BASE_URL=https://api.internal.albarakaturk.local
NEXT_PUBLIC_APP_BASE_URL=https://report.internal.albarakaturk.local
STORAGE_USE_LOCAL=false
DATABASE_ALLOW_LOCAL_DEV=false
```

---

## Next Steps

1. **Delete old code** (per CLAUDE.md section 5):
   - `apps/connector-agent/` → Silinecek
   - `apps/api/app/services/integrations.py` → Silinecek
   - `apps/api/app/services/report_factory.py` (most) → Refactor
   - `apps/api/app/orchestration/` (LangGraph) → Silinecek
   - Eski migration files → Cleanup

2. **Implement new LLM services**:
   - vLLM client wrapper (async)
   - Batch section generation worker (ARQ)
   - Hallucination detection pass

3. **Database migrations** (Alembic):
   - `downgrade base` (wipe old schema)
   - New migration with pivot v3 models (ReportDraft, ReportMetric, ReportSection, etc.)

4. **Setup Hocuspocus server**:
   - New `apps/collab-server/` (Node.js)
   - Y.js + Tiptap integration
   - JWT authentication

5. **Frontend integration**:
   - Tiptap + Y.js collaboration editor
   - Real-time metric references
   - WebSocket to Hocuspocus

6. **Testing**:
   - Health endpoint confirms all services connected
   - Sample LLM generation (Türkçe prompt)
   - Vector embedding & search
   - Real-time collab editing

---

## Credentials Security Checklist

- [ ] `.env.prod` never committed (add to `.gitignore`)
- [ ] Secrets read from environment (not defaults in settings.py)
- [ ] Secret manager integration (Kubernetes, Vault, etc.)
- [ ] Prod credentials rotated periodically
- [ ] No hardcoded passwords in code
- [ ] Health check timeout prevents hanging on unavailable services

---

## Key Architectural Changes

| Dimension | Before | After |
|-----------|--------|-------|
| **LLM Inference** | API call to Azure cloud | Local vLLM (on-prem GPU cluster) |
| **Embeddings** | Azure OpenAI (cloud) | Jina v4 (internal domain, multimodal) |
| **Vector Search** | Azure AI Search | pgvector (PostgreSQL native) |
| **Document Processing** | Azure Document Intelligence (OCR) | Removed (Q&A form input only) |
| **Storage** | Azure Blob Storage | MinIO (normal bucket) |
| **Job Queue** | ARQ + Redis (local) | ARQ + Redis (shared on-prem cluster) |
| **Realtime Collab** | Manual versioning | Y.js + Hocuspocus (automatic sync) |
| **Database** | Neon (cloud) | PostgreSQL (on-prem, pgvector extension) |
| **Air-gapped** | No | **Yes** ✓ |
| **Internet Dependency** | Azure APIs | None (internal only) |

---

## Migration Errors Expected (Normal)

1. **LLM Connection Failed** → Check vLLM service health
2. **pgvector Extension Not Found** → Ensure PostgreSQL has pgvector installed
3. **Redis Connection Refused** → Verify Redis password & network
4. **Jina Timeout** → Check internal domain DNS & firewall
5. **Settings Validator Error** → Check DATABASE_ALLOW_LOCAL_DEV & locale

All handled in `ON-PREMISE-CONFIG.md` troubleshooting section.

---

## References

- `CLAUDE.md` — Project scope & rules (Turkish)
- `.env.example` — Development defaults (all variables)
- `.env.prod.example` — Production template (secrets from manager)
- `ON-PREMISE-CONFIG.md` — Comprehensive setup & troubleshooting
- `apps/api/app/core/settings.py` — Pydantic model definition
- `compose.yaml` — Docker Compose dev environment
