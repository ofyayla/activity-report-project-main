# MinIO Linux — Path & Permission Fix

## ⚠️ Sorunlar

1. ❌ Binary `opt/minio` (relative) yerine `/opt/minio` (absolute) olmalı
2. ❌ Data dir `data/minio` (home directory) yerine `/data/minio` (root) olmalı  
3. ❌ Binary corrupt olmuş ("Exec format error")

---

## ✅ Fix Adım Adım

### 1️⃣ Mevcut Dosyaları Sil

```bash
# Home directory'deki hatalı dosyaları sil
rm -f ~/opt/minio
rm -rf ~/data/minio

# Kontrol
ls -la ~/ | grep -E "^d.*opt|^d.*data|minio"
# (Hiç çıkmalı)
```

### 2️⃣ Binary'yi Doğru Yere Kur

```bash
# Binary'yi indir
cd /tmp
rm -f minio
wget https://dl.min.io/server/minio/release/linux-amd64/minio

# Doğru yere koy (sudo gerekir)
sudo mv /tmp/minio /opt/minio
sudo chmod +x /opt/minio

# Kontrol
/opt/minio --version
# Output: minio version RELEASE.2026-04-XX
```

### 3️⃣ Data Directory Kur

```bash
# /data klasörü oluştur (sudo gerekir)
sudo mkdir -p /data/minio
sudo chmod 700 /data/minio

# Ownership (eğer user ile çalıştıracaksan)
sudo useradd -r -s /sbin/nologin minio 2>/dev/null || true
sudo chown -R minio:minio /data/minio

# Veya root ile çalıştıracaksan:
sudo chown root:root /data/minio
```

### 4️⃣ Test (Foreground)

```bash
# Root olarak çalıştır
sudo /opt/minio server /data/minio --console-address :9001

# Beklenen output:
#   API: http://127.0.0.1:9000  http://[::1]:9000
#   RootUser: minioadmin
#   RootPass: minioadmin
#   Web Console: http://127.0.0.1:9001
```

✅ **Çalışmıyorsa Ctrl+C ile durdur**

---

## 🔧 Eğer Hala "Exec format error"

### A) CPU Architecture Yanlış

```bash
# Sistemin mimarisi kontrol et
uname -m
# Output: x86_64 veya aarch64 (ARM) veya arm64

# x86_64 ise: https://dl.min.io/server/minio/release/linux-amd64/minio
# ARM ise:    https://dl.min.io/server/minio/release/linux-arm64/minio
```

**Doğru binary indir:**
```bash
# x86_64 (Intel/AMD)
wget https://dl.min.io/server/minio/release/linux-amd64/minio

# ARM64 (Raspberry Pi, Apple Silicon emulation)
wget https://dl.min.io/server/minio/release/linux-arm64/minio
```

### B) glibc Uyumsuzluğu

```bash
# Sistem glibc versiyonu kontrol et
ldd --version | head -1
# Output: ldd (GNU libc) 2.31

# Binary'nin gereksinimi kontrol et
/opt/minio --version 2>&1 | head -3
# Eğer "error loading" varsa, musl binary dene
```

**Musl binary (compatibility):**
```bash
wget https://dl.min.io/server/minio/release/linux-amd64-musl/minio
sudo mv minio /opt/minio && sudo chmod +x /opt/minio
/opt/minio --version
```

---

## 📋 Complete Fix Script

```bash
#!/bin/bash
set -e

echo "Fixing MinIO paths & permissions..."

# 1. Clean old files
echo "▶ Removing old files..."
rm -f ~/opt/minio
rm -rf ~/data/minio

# 2. Download fresh binary
echo "▶ Downloading MinIO..."
cd /tmp
rm -f minio
wget -q https://dl.min.io/server/minio/release/linux-amd64/minio

# Check if musl needed
if ! file minio | grep -q "ELF"; then
  echo "⚠ Binary corrupt, trying musl..."
  rm -f minio
  wget -q https://dl.min.io/server/minio/release/linux-amd64-musl/minio
fi

echo "✓ Binary downloaded"

# 3. Install to /opt
echo "▶ Installing to /opt..."
sudo mv /tmp/minio /opt/minio
sudo chmod +x /opt/minio

# Verify
if ! /opt/minio --version > /dev/null 2>&1; then
  echo "❌ Binary still broken"
  exit 1
fi
echo "✓ Binary working"

# 4. Create data directory
echo "▶ Creating /data/minio..."
sudo mkdir -p /data/minio
sudo chmod 700 /data/minio

# 5. Create minio user
echo "▶ Setting up minio user..."
sudo useradd -r -s /sbin/nologin minio 2>/dev/null || true
sudo chown -R minio:minio /data/minio

echo ""
echo "✅ Fix complete!"
echo ""
echo "Test:"
echo "  sudo /opt/minio server /data/minio --console-address :9001"
echo ""
```

Kaydet & çalıştır:
```bash
nano fix-minio.sh
chmod +x fix-minio.sh
./fix-minio.sh
```

---

## ✅ Final Kontrol

```bash
# 1. Binary location
ls -la /opt/minio
# -rwxr-xr-x 1 root root 110989496 Apr 18 10:19 /opt/minio

# 2. Data directory
ls -la /data/minio
# drwx------ 2 minio minio 4096 Apr 18 10:20 /data/minio

# 3. Run test
sudo /opt/minio server /data/minio --console-address :9001
# Should output: API: http://127.0.0.1:9000
```

---

## 🚀 Sonra: Systemd Setup

Eğer test başarılıysa, otomatik start:

```bash
sudo tee /etc/systemd/system/minio.service > /dev/null <<'EOF'
[Unit]
Description=MinIO Object Storage
After=network.target

[Service]
Type=notify
User=minio
Group=minio
ExecStart=/opt/minio server /data/minio --console-address :9001
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable minio
sudo systemctl start minio
sudo systemctl status minio
```

Logs:
```bash
sudo journalctl -u minio -f
```

---

## 🎯 Şu An Yapmanız Gereken

```bash
# Terminal'e yapıştır (copy-paste):

# Clean
rm -f ~/opt/minio && rm -rf ~/data/minio

# Download
cd /tmp && wget https://dl.min.io/server/minio/release/linux-amd64/minio

# Install
sudo mv /tmp/minio /opt/minio && sudo chmod +x /opt/minio

# Data dir
sudo mkdir -p /data/minio && sudo chmod 700 /data/minio
sudo useradd -r -s /sbin/nologin minio 2>/dev/null || true
sudo chown -R minio:minio /data/minio

# Test
/opt/minio --version
sudo /opt/minio server /data/minio --console-address :9001
```

✅ Eğer "API: http://127.0.0.1:9000" görürsen başarılı!
