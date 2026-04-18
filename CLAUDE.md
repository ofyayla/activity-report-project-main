# CLAUDE.md — Veni AI Report Factory (Pivot v3)

Bu dosya, projenin pivotlanmış yeni yönünü ve implementasyon planını tanımlar. Mevcut kod tabanı **eski Azure/ERP-odaklı mimariye aittir ve büyük kısmı silinecektir**. Yeni mimariye göre çalışırken bu dokümanı referans al.

---

## 1. Proje Amacı (Pivot Sonrası)

**Ne yapıyoruz:** Bir bankanın **Entegre Faaliyet Raporu** ve **Sürdürülebilirlik Raporu** taslaklarını, insan kontrolü ile finalize edilebilecek şekilde, lokal LLM desteği ile hızlı üreten bir karar destek aracı.

**İki faz:**
- **Faz 1 — İlk Taslak:** Kullanıcı Excel ile veya UI formu üzerinden soru-cevap seti girer. Sistem, sabit bölüm şablonlarına göre her bölümü batch olarak lokal LLM'e ürettirir.
- **Faz 2 — Bölüm Editleme:** Kullanıcı Notion-benzeri rich text editor'de istediği bölümü seçip serbest prompt ile yeniden yazdırır. Undo, yorum, versiyon geçmişi, yıl bazında klonlama destekli.

**Kritik kısıtlar:**
- Tamamen **on-premise, air-gapped**. İnternet yok, cloud bağımlılığı yok.
- **Hiçbir dış veri kaynağı kullanılmaz.** Yalnızca kullanıcının sağladığı Q&A input'undan içerik üretilir.
- **Nihai karar verici değil** — insan onayı olmadan yayınlanmaz.

---

## 2. Infrastructure — Ayakta Olan Servisler

### 2.1 vLLM (Lokal LLM)

- **Endpoint:** `http://localhost:8821/v1` (OpenAI-compatible)
- **Model:** `Qwen/Qwen3.6-35B-A3B-FP8` (MoE, ~3B aktif parametre)
- **Kullanım:** OpenAI Python SDK ile doğrudan çağrılır (`AsyncOpenAI(base_url=..., api_key="not-needed")`)
- **Donanım:** Dev=H100 (80GB), Prod=H200 (141GB)

### 2.2 pgvector (Vector DB + Regular PostgreSQL)

Ayakta olan pgvector-destekli PostgreSQL instance:

```python
PGVECTOR_HOST     = os.getenv("PGVECTOR_HOST",     "10.144.100.204")
PGVECTOR_PORT     = os.getenv("PGVECTOR_PORT",     "25432")
PGVECTOR_USER     = os.getenv("PGVECTOR_USER",     "vector_user1")
PGVECTOR_PASSWORD = os.getenv("PGVECTOR_PASSWORD", "vector_78s64+w2")
PGVECTOR_DATABASE = os.getenv("PGVECTOR_DATABASE", "vectordb1")

PGVECTOR_CONNECTION_STRING = (
    f"postgresql+psycopg2://{PGVECTOR_USER}:{PGVECTOR_PASSWORD}"
    f"@{PGVECTOR_HOST}:{PGVECTOR_PORT}/{PGVECTOR_DATABASE}"
)
```

Not: Prod'da credential'lar `.env` veya secret manager'dan okunmalı. Yukarıdaki default'lar dev içindir.

### 2.3 Redis (Queue + Realtime State)

Ayakta olan Redis instance (ARQ worker queue + Hocuspocus realtime state):

```python
import redis

REDIS_HOST     = os.getenv("REDIS_HOST",     "10.144.100.204")
REDIS_PORT     = os.getenv("REDIS_PORT",     "46379")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "O*+78sYtsr")

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=int(REDIS_PORT),
    password=REDIS_PASSWORD,
    socket_connect_timeout=2,
    socket_timeout=2,
    decode_responses=True
)

# Bağlantı testi
try:
    redis_client.ping()
    print("Redis ayakta ✅")
except Exception as e:
    print("Redis erişilemiyor ❌", e)
```

**Kullanım:**
- **ARQ job queue:** LLM generation batch worker'lar (bölüm üretim, çeviri, hallucination check)
- **Session state:** Hocuspocus server'ın realtime collaboration state'i (Y.js document snapshots)
- **Cache:** İngilizce çeviriler, embedding results

Not: Prod'da credential'lar `.env` veya secret manager'dan okunmalı. Yukarıdaki default'lar dev içindir.

### 2.4 Jina Embedding (Text + Image Embedding)

Ayakta olan Jina Embedding v4 instance (multimodal embedding):

```python
import requests

JINA_EMBEDDING_BASE = os.getenv("JINA_EMBEDDING_BASE", 
                                 "https://jina-embedding.aiops.albarakaturk.local")
TEXT_ENDPOINT  = f"{JINA_EMBEDDING_BASE}/embed/text"
IMAGE_ENDPOINT = f"{JINA_EMBEDDING_BASE}/embed/image"

# Text embedding — single prompt
def embed_text_single(model_name: str, text: str):
    payload = {"model": model_name, "prompt": text}
    resp = requests.post(TEXT_ENDPOINT, json=payload)
    resp.raise_for_status()
    return resp.json()

# Text embedding — batch
def embed_text_batch(model_name: str, texts: list):
    payload = {
        "model": model_name,
        "texts": texts,
    }
    resp = requests.post(TEXT_ENDPOINT, json=payload)
    resp.raise_for_status()
    return resp.json()

# Image embedding
def embed_image(model_name: str, queries: list, image_paths: list):
    """
    Embed local images + text queries.
    image_paths: list of file paths → converted to data-URI base64.
    """
    import base64
    
    def image_to_base64(path: str) -> str:
        with open(path, "rb") as f:
            data = f.read()
        b64 = base64.b64encode(data).decode('utf-8')
        ext = path.split('.')[-1]
        return f"data:image/{ext};base64,{b64}"
    
    images_b64 = [image_to_base64(p) for p in image_paths]
    payload = {
        "model": model_name,
        "queries": queries,
        "images_base64": images_b64
    }
    resp = requests.post(IMAGE_ENDPOINT, json=payload)
    resp.raise_for_status()
    return resp.json()

# Örnekler
model = "jina-embedding-v4"  # multimodal
print(embed_text_single(model, "Merhaba dünya!"))
print(embed_text_batch(model, ["Soru 1", "Soru 2"]))
print(embed_image(model, ["kedi", "köpek"], ["cat.jpg", "dog.png"]))
```

**Kullanım:**
- Q&A Set'teki cevapları embedding'le pgvector'a kaydetme
- Semantic search for retrieval-augmented generation (RAG)
- Image analysis in sustainability reports (e.g., carbon footprint visuals)

Not: Prod'da base URL ve credentials `.env` veya secret manager'dan okunmalı.

### 2.5 Eklenecek Servisler (M1'de kurulacak)

- **Hocuspocus server:** Real-time collaboration için — yeni `apps/collab-server/` (Node.js)
- **MinIO:** Normal bucket (WORM yok) — Excel uploads + published snapshots için
- **Redis + ARQ:** Batch worker queue (Redis + ARQ, Redis ayakta, ARQ workerları kurulacak)

---

## 3. Tech Stack

| Katman | Teknoloji | Not |
|---|---|---|
| Backend API | FastAPI + Pydantic v2 + SQLAlchemy 2.0 + Alembic | Mevcut iskelet korunuyor |
| Frontend | Next.js 16 (App Router) + React 19 + TypeScript + Tailwind 4 | Mevcut korunuyor |
| Editor | **Tiptap** + ProseMirror + Y.js + CollaborationCursor | Yeni |
| Realtime Collab | **Hocuspocus server** (Node.js) + Redis + PostgreSQL | Yeni |
| LLM Runtime | **vLLM** (yerel, `localhost:8821`) | Yeni |
| LLM Client | `openai` Python SDK (OpenAI-compatible endpoint) | Yeni |
| Embeddings | **Jina Embedding v4** (text + image, multimodal) | Ayakta |
| Vector Search | **pgvector** (zaten ayakta) | Yeni |
| Queue | Redis + ARQ | Mevcut |
| Storage | MinIO (normal bucket) veya filesystem | Değişti |
| Excel Parse | `openpyxl` + `pandas` | Yeni |
| DOCX Export | `python-docx` | Yeni |
| MD Export | `tiptap-markdown` (frontend) veya `mistune` (backend) | Yeni |

---

## 4. Mimari Kararlar — Locked

Aşağıdaki kararlar netleşti; değiştirmek isteniyorsa önce kullanıcıya sor.

| Konu | Karar |
|---|---|
| Real-time collab | **Y.js + Hocuspocus + Tiptap Collaboration extension** (section-level lock değil) |
| LLM runtime | Mevcut vLLM `http://localhost:8821`, model `Qwen/Qwen3.6-35B-A3B-FP8` |
| Kriptografik imzalama | **Uygulanmayacak** |
| WORM storage | **Uygulanmayacak** — normal MinIO/filesystem |
| PDF export | **Uygulanmayacak** — DOCX + Markdown yeterli |
| Review workflow | **Tek aşamalı** (draft → review → approved → published) |
| Audit | Basit `AuditEvent` tablosu — hash chain yok, retention policy yok (Faz 1'de) |
| Worker timeout/retry | ARQ: 120-180s timeout, 3 retry, exponential backoff (5s, 15s, 45s) |
| Dil | TR (master) + EN (LLM çevirisi ile türetilir) |
| YoY | Her yıl yeni `ReportDraft`, `parent_draft_id` ile linkli; clone endpoint'i |
| Brand Kit | Yok, tek firma |

---

## 5. Kaldırılacak Legacy Componentler (M1/M2 Cleanup)

Bu dizinler ve dosyalar **tamamen silinecek:**

```
apps/connector-agent/                              # Tüm klasör (SAP/Logo/Netsis agent'ı)
apps/api/app/services/integrations.py              # ~1563 satır
apps/api/app/services/report_factory.py            # ~3456 satır (büyük kısmı)
apps/api/app/services/report_factory_template.html.jinja
apps/api/app/services/verifier.py                  # Yerine hallucination check
apps/api/app/services/retrieval.py                 # Yerine pgvector-based retrieval
apps/api/app/orchestration/                        # LangGraph workflow tamamen
apps/api/app/api/routes/integrations.py
apps/api/app/api/routes/runs.py                    # Rapor-odaklı yeni route'lar
```

**Silinecek modeller (`apps/api/app/models/core.py`):**
- `BrandKit`, `ConnectorAgent`, `IntegrationConfig`, `ConnectorSyncJob`, `ConnectorOperationRun`
- `CanonicalFact`, `KpiSnapshot`
- `ReportPackage`, `ReportArtifact`, `ReportVisualAsset`
- `Claim`, `ClaimCitation`, `VerificationResult`, `CalculationRun`

**Silinecek bağımlılıklar (pyproject.toml):**
- `langgraph`, `langchain-*`
- `weasyprint`, `reportlab`, `pypdf`
- `azure-*` paketleri tamamı

**Alembic:** `downgrade base` sonrası yeni model ile sıfırdan migrate. Production data yok, risk yok.

**Not:** Kökte `AGENTS.md` mevcut — eski mimariye ait. M1'de silinecek veya yeni mimariye göre yeniden yazılacak.

---

## 6. Yeni Veri Modeli

```
Company (tek firma)
User, UserRole (RBAC)
ReportTemplate (rapor tipi + dil bazlı bölüm şablonları, prompt'lar)
TranslationGlossary (TR↔EN kurumsal terminoloji)

ReportDraft
  ├─ reporting_year, report_type, language, status
  ├─ parent_draft_id (önceki yıl), master_draft_id (TR↔EN link)
  ├─ QuestionAnswerSet → QuestionAnswerItem
  │    section_mapping[], review_status
  │
  ├─ ReportMetric (global metrik — single source of truth)
  │    ├─ metric_code, display_name_tr/en, type, unit
  │    ├─ value_numeric/text/date, format_spec_tr/en
  │    ├─ formula, depends_on_metric_ids (computed metrics)
  │    └─ MetricRevision (immutable revizyon zinciri)
  │
  ├─ ReportSection
  │    ├─ current_version_id
  │    └─ ReportSectionVersion (immutable zincir)
  │         content_json (Tiptap), generation_mode, prompt_used
  │         parent_version_id (undo için)
  │
  │    └─ SectionComment (threaded, anchor_json ile Tiptap pozisyonuna bağlı)
  │
  ├─ HallucinationWarning (post-gen LLM check sonuçları)
  ├─ LLMInteraction (her LLM çağrısı audit izi)
  └─ ReviewDecision (tek aşamalı review)

PublishedReportSnapshot (imzasız frozen snapshot)
  content_json, content_docx, content_markdown
  metric_snapshot_json (publish anındaki metrik değerleri)

AuditEvent (basit — hash chain yok)
  actor, event_type, event_name, resource, before_state, after_state
```

**Kritik design:**
- **Global metric system:** Metrik değeri bir yerde değişince raporun her referansında otomatik güncellenir. Tiptap'te `metricReference` custom node'u, pgvector/DB'den değeri runtime'da çeker.
- **Version chain:** Her LLM edit yeni `ReportSectionVersion` oluşturur, eskisi silinmez. `current_version_id` pointer'ı değişir. Undo = parent'a geri dön.

---

## 7. LLM Generation Kuralları

### 7.1 Metric Injection Pattern

**System prompt'a mevcut metrikler enjekte edilir:**
```
Kullanılabilir metrikler:
  - {{TOTAL_EMPLOYEES}}: Toplam Çalışan Sayısı (şu an: 1,247)
  - {{SCOPE2_EMISSIONS_2025}}: Scope 2 Emisyonu 2025 (şu an: 12,450 tCO2e)

KURAL: Metriklerden bahsettiğinde AYNI syntax ile referans ver, 
       değeri DOĞRUDAN yazma. 
       ✓ 'Bu yıl {{TOTAL_EMPLOYEES}} çalışan istihdam ettik'
       ✗ 'Bu yıl 1.247 çalışan istihdam ettik'

Metriklerde olmayan yeni sayısal veri ÜRETME.
```

**Post-process:** `{{METRIC_CODE}}` pattern'leri regex ile yakalanıp Tiptap `metricReference` node'una dönüştürülür.

### 7.2 Hallucination Guard (Zorunlu)

Her LLM generation sonrası ikinci LLM pass ile doğrulama:
```
Aşağıdaki METİN yalnızca aşağıdaki BAĞLAM'dan üretilmiş olmalı.
Bağlamda olmayan sayısal veri, isim, tarih veya iddia var mı?
JSON döndür: { "has_hallucinations": bool, "flagged_spans": [...] }
```
Flag'lenen span'lar UI'da sarı highlight ile gösterilir. Zorunlu block değil — kullanıcı uyarısı.

### 7.3 Bilingual Translation Rules

TR→EN çevirisinde zorunlu kurallar:
- Tüm `{{METRIC_CODE}}` placeholder'ları AYNEN korunur
- Sayısal değerler ve birimler değişmez
- TranslationGlossary'deki zorunlu terim eşlemeleri uygulanır
- BDDK/bankacılık İngilizce terminolojisi kullanılır

---

## 8. Y.js + Hocuspocus Entegrasyonu

**Akış:**
```
Tiptap (frontend) ↔ Y.js doc ↔ WebSocket ↔ Hocuspocus Server ↔ PostgreSQL + Redis
```

**Hocuspocus server:** Yeni `apps/collab-server/` dizini, Node.js, kendi Dockerfile'ı. Port 1234. JWT authentication, section edit permission check.

**Snapshot stratejisi:**
- Y.js state in-memory + Redis ile multi-instance
- Her 60 saniyede veya explicit "save" butonunda `ReportSectionVersion` olarak PostgreSQL'e frozen snapshot

**Undo layering:**
- Y.js native undo (her kullanıcı için anlık, canlı edit'ler)
- Version-level undo (LLM edit gibi büyük sıçramalar — parent_version_id zinciri)

---

## 9. İmplementasyon Roadmap

| Milestone | Süre | İçerik |
|---|---|---|
| **M1** Infra + Cleanup | 1 hafta | vLLM client, pgvector bağlantısı, Hocuspocus server kurulumu, MinIO, legacy kod silme |
| **M2** Model + Auth | 1.5 hafta | Yeni SQLAlchemy modelleri, Alembic fresh migration, RBAC, AuditEvent |
| **M3** Q&A Pipeline | 1.5 hafta | Excel upload (openpyxl), Q&A form UI, validation, glossary admin |
| **M4** Metric System | 2 hafta | ReportMetric CRUD, sidebar UI, computed metrics (safe expression evaluator), WebSocket push |
| **M5** LLM Generation | 2 hafta | vLLM client, batch section worker, metric injection, hallucination check |
| **M6** Tiptap + Y.js | 3 hafta | Custom metricReference node, Hocuspocus entegrasyonu, version history, diff, comments |
| **M7** LLM Edit + Undo | 1 hafta | Edit modal, preview (accept/reject), version chain undo |
| **M8** Bilingual | 1.5 hafta | TR→EN translation, glossary injection, locale formatting |
| **M9** YoY Cloning | 0.5 hafta | Clone from previous year, compare view |
| **M10** Review + Publish | 1 hafta | Single-stage review, PublishedReportSnapshot |
| **M11** Export | 0.5 hafta | DOCX (python-docx) + Markdown |
| **M12** Polish | 1 hafta | E2E Playwright testleri, admin panel, deployment docs |

**Toplam: ~16 hafta (tek dev) / ~10-11 hafta (iki dev paralel)**

---

## 10. Kritik Kurallar — Her İmplementasyonda Uyulacak

1. **İnternet/dış veri yok.** Kod asla `httpx.get("https://...")`, web scraping, external API call içermez. Sadece `localhost:8821` (vLLM) ve pgvector/Redis/MinIO lokal servisler.
2. **Metrikler single source of truth.** Rapor metninde sayı görürsen `{{METRIC_CODE}}` referansı mı diye kontrol et. Doğrudan sayı enjeksiyonu kabul değil.
3. **LLM çıktısı her zaman audit'lenir.** Her LLM çağrısı `LLMInteraction` tablosuna prompt+response+tokens ile kaydedilir.
4. **Versiyonlar silinmez.** `ReportSectionVersion`, `MetricRevision` immutable. Silme yerine yeni kayıt + pointer update.
5. **Turkish first, English second.** Default locale TR. EN yalnızca TR onaylandıktan sonra translation flow ile üretilir.
6. **Published = frozen.** `PublishedReportSnapshot` oluşturulduktan sonra o content değişmez. Yeni revizyon yeni snapshot.
7. **Test öncelikle Türkçe promptlarla.** Model Türkçe performansı kritik — her yeni prompt template için manuel örnekle test et.

---

## 11. Çalışma Alışkanlıkları

- Mevcut kod tabanında değişiklik yaparken **önce bu dosyadaki "Kaldırılacak Legacy Componentler" listesi ile çakışıp çakışmadığını kontrol et**. Eğer dokunulan kod silinecek listede ise, düzeltmek yerine silmeyi değerlendir.
- Yeni Python bağımlılığı eklerken: air-gapped ortam unutulmasın. Package wheel'ları önceden indirilebilir olmalı.
- Frontend bağımlılıkları için benzer: pnpm offline mirror desteği düşün.
- Prompt şablonları DB'de (`ReportTemplate.system_prompt` vb.) — koda hardcode etme.
- LLM call'lar her zaman async. Sync wrapper yazma.

---

## 12. Açık Kalan / İleride Değerlendirilecek Konular

- **Admin UI:** Non-developer için prompt template editörü (M12 sonrası veya Faz 2)
- **Golden reports:** Geçmiş yılların nihai raporlarını LLM için reference example olarak inject
- **Readability scoring:** Türkçe Ateşman formülü + İngilizce Flesch-Kincaid
- **Spell check:** Hunspell TR+EN sözlüğü (air-gapped kurulum uyumlu)
- **Crypto signing + WORM storage:** Faz 2'ye ertelendi, gerekirse compliance gereksinimi netleşince eklenir

---

## 13. İletişim Bağlamı

- Proje sahibi Türkçe çalışır — teknik çıktıları Türkçe açıklayarak göster.
- Kod, type name, değişken adları İngilizce (standard convention).
- Commit mesajları, doc yorumları Türkçe yazılabilir.
- Raporlanan nihai ürün hem TR hem EN üretecek; glossary/terminoloji kurumsal BDDK/bankacılık jargonuna uygun olmalı.
