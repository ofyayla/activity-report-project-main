# MinIO vs Alternatifleri — Storage Seçim Rehberi

## 📦 MinIO Projede Neler İçin Kullanılacak?

### Kullanım Alanları (Veni AI Report Factory)

```
User Uploads
    ↓
1️⃣ Excel dosyaları (Q&A input)
   └─ report-uploads bucket
   └─ 10-100 MB/dosya, ~100 dosya/yıl

2️⃣ Resimler (sustainability reports)
   └─ report-uploads bucket
   └─ PNG, JPG, ~5-50 MB/resim

3️⃣ Yayınlanan Report Snapshot'ları
   └─ report-snapshots bucket
   └─ DOCX, Markdown, JSON (Tiptap content)
   └─ ~1-10 MB/snapshot, versioning

4️⃣ Sistemin ürettiği artifact'lar
   └─ Generated charts, embeddings cache
   └─ Temporary files (cleanup policy)
```

### Storage Gerekçeleri

| Gereksinim | MinIO | Açıklama |
|-----------|-------|----------|
| **On-Premise** | ✅ | Cloud'u reddetmişiz, MinIO %100 on-prem |
| **S3 API** | ✅ | Python SDK'lar direkt desteği |
| **Versioning** | ✅ | Report history takibi |
| **Access Control** | ✅ | Bucket-level policies |
| **Performance** | ✅ | High throughput (LAN) |
| **Ease of Use** | ✅ | Simple kurulum, web console |

---

## 🔄 Alternatif Seçenekler

### 1️⃣ **Local Filesystem (Simplest)**

**Nasıl çalışır:**
```python
# apps/api/storage.py
from pathlib import Path

class LocalStorage:
    def __init__(self, base_path="/data/reports"):
        self.base_path = Path(base_path)
    
    def upload_file(self, bucket: str, filename: str, data: bytes):
        path = self.base_path / bucket / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    
    def download_file(self, bucket: str, filename: str) -> bytes:
        path = self.base_path / bucket / filename
        return path.read_bytes()
```

**Pros:**
- ✅ Sıfır kurulum
- ✅ Sıfır dependency
- ✅ Hızlı local read/write
- ✅ Dosya sistemden native backup (rsync, tar)

**Cons:**
- ❌ Horizontal scale'le sıkıntı (multi-server)
- ❌ Web console yok
- ❌ S3 API uyumluluğu yok
- ❌ Permission management manual
- ❌ CORS/public URL sıkıntılı
- ❌ Distributed system'de senkronizasyon sıkıntı

**Use case:**
```
Development ortamı (single server)
Small installation (<10GB)
Web UI'den upload yok
```

---

### 2️⃣ **Ceph (Enterprise)**

**Nedir:**
Açık kaynak distributed storage (Facebook, Red Hat, OpenStack)

**Pros:**
- ✅ Massive scale (petabytes)
- ✅ Multi-server distribution
- ✅ S3, Swift API uyumluluğu
- ✅ Data replication & fault tolerance
- ✅ On-premise fully

**Cons:**
- ❌ Kompleks setup (3+ server gerekir)
- ❌ Heavy resource (CPU, RAM)
- ❌ Operations overhead (cluster management)
- ❌ Learning curve (CRUSH, PGs, placement groups)

**Cost:** Open source but operational complexity

**Use case:**
```
10+ TB veri
Multi-server deployment
High availability & disaster recovery gerekli
```

---

### 3️⃣ **Wasabi / Backblaze B2 (Cloud, but Private)**

**Nedir:**
S3-compatible cloud storage (MinIO'nun cloud alternatifi)

**Pros:**
- ✅ Fully managed
- ✅ S3 API compatible
- ✅ No ops overhead
- ✅ Cheaper than AWS S3

**Cons:**
- ❌ **YOK!** Proje air-gapped olmalı
- ❌ İnternet gerekli
- ❌ External vendor dependency
- ❌ CLAUDE.md'de explicitly forbidden

**Not:** Projede kullanılamaz (on-premise constraint)

---

### 4️⃣ **NFS / SMB (Shared Network Storage)**

**Nedir:**
Network File System (shared folder like Windows)

**Setup:**
```bash
# Server'da
sudo apt install nfs-kernel-server
sudo tee /etc/exports > /dev/null <<'EOF'
/data/reports 10.144.100.0/24(rw,sync,no_subtree_check)
EOF
sudo exportfs -a
sudo systemctl restart nfs-kernel-server

# Client'ta
sudo mount -t nfs 10.144.100.204:/data/reports /mnt/reports
```

**Pros:**
- ✅ Basit mount işlemi
- ✅ Transparent file access
- ✅ Multi-server access
- ✅ Cheap (commodity hardware)

**Cons:**
- ❌ No S3 API (Django/Celery uyumsuz)
- ❌ Performance latency (network)
- ❌ Locking issues (concurrent writes)
- ❌ No built-in versioning
- ❌ Backup/replication manual

**Use case:**
```
Legacy systems (NFS-based)
Simple file shares
No API requirement
```

---

### 5️⃣ **PostgreSQL BYTEA (Database)**

**Nedir:**
Dosyaları direkt PostgreSQL'e kaydetme

**Code:**
```python
from sqlalchemy import Column, LargeBinary
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class ReportFile(Base):
    __tablename__ = "report_files"
    id = Column(Integer, primary_key=True)
    filename = Column(String)
    content = Column(LargeBinary)  # Dosya burada
    bucket = Column(String)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

# Kaydet
db.add(ReportFile(filename="report.xlsx", content=file_bytes, bucket="uploads"))

# Oku
file = db.query(ReportFile).filter_by(filename="report.xlsx").first()
data = file.content
```

**Pros:**
- ✅ Sıfır kurulum (zaten PostgreSQL var!)
- ✅ ACID transactions
- ✅ Built-in backup (database backup)
- ✅ Fine-grained permission (table-level)

**Cons:**
- ❌ Disk I/O overhead (large files)
- ❌ Backup saatleri uzun (tüm DB dump)
- ❌ S3 API uyumsuz
- ❌ Restoration sıkıntılı (part recovery)
- ❌ Performance degrade (multi-GB dosyalar)
- ❌ Database size expansion (200GB+ olabilir)

**Limit:**
PostgreSQL blob'lar için optimize değil. >1GB dosyalar problematik.

**Use case:**
```
Çok küçük dosyalar (<100MB total)
Metadata bağlantı önemli
Backup önemli
```

---

## 🎯 Recommendation Matrix

| Seçenek | Dev | Small Prod | Large Prod | Multi-Server | Cost |
|---------|-----|-----------|-----------|--------------|------|
| **Local FS** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ❌ | ❌ | $0 |
| **MinIO** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | $0 |
| **Ceph** | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Ops |
| **NFS** | ⭐⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐ | $$ |
| **PostgreSQL** | ⭐⭐⭐ | ⭐ | ❌ | ⭐ | $0 |

---

## 🤔 Neden MinIO Seçilmiş?

**Proje Constraints:**
1. ✅ On-premise (cloud yok)
2. ✅ Air-gapped (internet yok)
3. ✅ Single binary (kurulum basit)
4. ✅ S3 API (Python SDK uyumlu)
5. ✅ Web console (user-friendly)
6. ✅ Scalable (gelecekte multi-server)

**Trade-off Analysis:**
- **Vs Local FS:** MinIO → scalability + API
- **Vs Ceph:** MinIO → simplicity (Ceph'e upgrade edilebilir)
- **Vs NFS:** MinIO → API + versioning
- **Vs PostgreSQL:** MinIO → large files + performance

**CLAUDE.md Decision:**
```markdown
| Storage | Karar |
|---------|-------|
| PDF export | **Uygulanmayacak** — DOCX + Markdown yeterli |
| WORM storage | **Uygulanmayacak** — normal MinIO bucket |
```

✅ **MinIO kilitli seçim** (section 4, "Mimari Kararlar — Locked")

---

## 💡 Hybrid Approach: Combine Multiple

### Scenario 1: MinIO + Local Cache

```python
# Temp files → local FS (hız)
# Permanent files → MinIO (persistence)

class HybridStorage:
    def __init__(self):
        self.local = LocalStorage("/tmp/cache")
        self.minio = MinIOStorage("10.144.100.204:9000")
    
    def upload_file(self, bucket: str, filename: str, data: bytes):
        # Cache locally first
        self.local.upload_file(bucket, filename, data)
        
        # Upload to MinIO (background)
        background_task = asyncio.create_task(
            self.minio.upload_file(bucket, filename, data)
        )
        
        return await background_task
```

**Use:** Large file uploads (progressive save)

---

### Scenario 2: MinIO + PostgreSQL Hybrid

```python
# Metadata → PostgreSQL (searchable)
# Blobs → MinIO (efficient)

class ReportSnapshot(Base):
    __tablename__ = "report_snapshots"
    id = Column(Integer, primary_key=True)
    minio_key = Column(String)  # "report-snapshots/2025-01-report.docx"
    version = Column(Integer)
    content_hash = Column(String)  # Integrity check
    created_at = Column(DateTime)

# Query örneği
snapshots = db.query(ReportSnapshot).filter(
    ReportSnapshot.created_at > date
).all()  # DB'den hızlı

# Dosya oku
for snap in snapshots:
    content = minio.download_file("report-snapshots", snap.minio_key)
```

**Use:** Metadata + large blobs

---

## 📊 Storage Usage Projection

**Year 1 (Baseline):**
```
Excel uploads:        500 files × 50 MB = 25 GB
Report snapshots:     500 × 10 MB = 5 GB
Images:               1000 × 5 MB = 5 GB
Temp/cache:           50 GB (cleanup hourly)
─────────────────────────────────
Total:                ~85 GB (MinIO: 35 GB persistent)
```

**Year 2 (Growth):**
```
Projected 2x growth → 170 GB
MinIO handles easily (single server)
```

**Year 3+ (Scale):**
```
Multi-client deployment
MinIO distributed mode gerekebilir
→ Ceph upgrade yolu açık
```

---

## 🔐 Security Considerations

### MinIO vs Local FS

| Aspect | MinIO | Local FS |
|--------|-------|----------|
| **Access Control** | Bucket policies | Unix permissions |
| **Audit** | Access logs | Filesystem logs |
| **Encryption** | At-rest (optional) | Disk encryption |
| **Versioning** | Built-in | Manual (snapshots) |

---

## ✅ Final Decision Tree

```
Storage seçimi için:

1. Dev machine alone?
   → Local FS (fast, simple)

2. Single production server?
   → MinIO (scalable, API, simple)

3. Multi-server deployment?
   → MinIO distributed (or upgrade Ceph later)

4. Petabyte scale + high availability?
   → Ceph (complex but powerful)

5. Very small files only?
   → PostgreSQL BYTEA (meta + blob combined)
```

**Veni AI için:** MinIO ✅ (node 2: Single prod server, future-proof)

---

## 🚀 Implementation Decision

**LOCKED (per CLAUDE.md):**
- Storage: **MinIO** (normal bucket, no WORM)
- No PostgreSQL blobs
- No cloud alternatives
- No NFS

**Migration path if needed:**
```
MinIO (Single) → MinIO (Distributed) → Ceph (if 100TB+)
```

**Never:**
- Don't use Azure Blob (cloud forbidden)
- Don't split files across systems (complexity)
- Don't use NFS (legacy)
