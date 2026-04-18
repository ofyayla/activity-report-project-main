# MinIO — Linux Quick Start

## Sorun: "Exec format error"

**Sebep:** Binary dosya corrupt veya yanlış format

**Çözüm:** Yeniden indir ve doğru şekilde kur

---

## 1️⃣ MinIO Binary İndir (Taze)

```bash
# Eski dosyayı sil
sudo rm -f /opt/minio

# Taze binary indir
cd /tmp
wget https://dl.min.io/server/minio/release/linux-amd64/minio

# Kontrol et
file minio
# Output: minio: ELF 64-bit LSB executable, x86-64, version 1 (SYSV)...
```

---

## 2️⃣ Sisteme Kur

```bash
# /opt klasörüne taşı
sudo mv /tmp/minio /opt/minio

# Çalıştırılabilir yap
sudo chmod +x /opt/minio

# Owner düzelt
sudo chown root:root /opt/minio

# Kontrol et
/opt/minio --version
# Output: minio version RELEASE.2026-04-XX...
```

---

## 3️⃣ Data Klasörü Oluştur

```bash
# MinIO için data dizini
sudo mkdir -p /data/minio
sudo chmod 700 /data/minio

# Eğer çalıştıracak user varsa (önerilen)
sudo useradd -r -s /sbin/nologin minio 2>/dev/null || true
sudo chown -R minio:minio /data/minio
```

---

## 4️⃣ **Foreground'da Test Et** (İlk kez)

```bash
# Root olarak çalıştır (test için)
sudo /opt/minio server /data/minio --console-address :9001
```

**Beklenen output:**
```
  API: http://127.0.0.1:9000  http://[::1]:9000
  RootUser: minioadmin
  RootPass: minioadmin

  Web Console: http://127.0.0.1:9001
  Command-line: mc alias set 'myminio' 'http://127.0.0.1:9000' 'minioadmin' 'minioadmin'
```

✅ **Çalışıyorsa:** Ctrl+C ile durdur, adım 5'e git

❌ **Yine hata alırsa:**
```bash
# Binary'nin mimarisi kontrol et
ldd /opt/minio
# Eğer "not found" varsa, glibc uyumsuz
# Alternatif: musl binary indir
wget https://dl.min.io/server/minio/release/linux-amd64-musl/minio
```

---

## 5️⃣ Systemd Service'i Kur (Otomatik başlat)

```bash
# Service dosyası oluştur
sudo tee /etc/systemd/system/minio.service > /dev/null <<'EOF'
[Unit]
Description=MinIO Object Storage
Documentation=https://docs.min.io
Wants=network-online.target
After=network-online.target
AssertFileNotEmpty=/etc/default/minio

[Service]
Type=notify
User=minio
Group=minio
ProtectProcessNoaccess=true
ProtectSystem=full
LimitNOFILE=65536
ExecStartPre=/bin/sh -c 'echo "MinIO starting..."'
ExecStart=/opt/minio server /data/minio --console-address :9001
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=minio

[Install]
WantedBy=multi-user.target
EOF

# Default config (zorunlu)
sudo tee /etc/default/minio > /dev/null <<'EOF'
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
EOF
```

**Enable & start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable minio
sudo systemctl start minio

# Status kontrol
sudo systemctl status minio -l
```

**Logs kontrol:**
```bash
sudo journalctl -u minio -f --no-pager
```

---

## 6️⃣ Console'a Gir & Setup Yap

**Browser açın:**
```
http://10.144.100.204:9001
```

**Login:**
- Username: `minioadmin`
- Password: `minioadmin`

### Buckets Oluştur

1. Sol menü → **Buckets** → **Create Bucket**
2. Name: `report-uploads` → **Create**
3. Aynısını tekrarla: `report-snapshots`

### Access Key Oluştur

1. Sol menü → **Access Keys**
2. **Create Access Key**
3. Auto-generated access key & secret key'i **kopyala**
4. `.env` dosyasında set et:
   ```env
   MINIO_ACCESS_KEY=<access-key>
   MINIO_SECRET_KEY=<secret-key>
   ```

---

## 7️⃣ Python SDK Test

```bash
pip install boto3

python3 << 'EOF'
import boto3

s3 = boto3.client(
    's3',
    endpoint_url='http://10.144.100.204:9000',
    aws_access_key_id='your-access-key',
    aws_secret_access_key='your-secret-key'
)

# Buckets list
response = s3.list_buckets()
for bucket in response['Buckets']:
    print(f"Bucket: {bucket['Name']}")

# Test upload
with open('/tmp/test.txt', 'w') as f:
    f.write('Hello MinIO!')

s3.upload_file('/tmp/test.txt', 'report-uploads', 'test.txt')
print("✓ Upload successful")
EOF
```

---

## 8️⃣ Verify

```bash
# API endpoint test
curl -s http://10.144.100.204:9000/minio/health/live
# Output: {"status":"ok"}

# Console test
curl -s http://10.144.100.204:9001 | head -5

# Service status
sudo systemctl status minio
```

---

## 🆘 Troubleshooting

### "Exec format error" (Hala Hata)

```bash
# Glibc versyon kontrolü
/opt/minio --version 2>&1 | head -1

# Sistem glibc'si kontrol et
ldd --version | head -1

# Eğer eski glibc varsa, musl binary indir
wget https://dl.min.io/server/minio/release/linux-amd64-musl/minio
sudo mv minio /opt/minio && sudo chmod +x /opt/minio
```

### "Permission denied"

```bash
sudo chmod +x /opt/minio
sudo chown root:root /opt/minio
```

### Data directory permission

```bash
sudo chown -R minio:minio /data/minio
sudo chmod 700 /data/minio
```

### Port 9000 / 9001 already in use

```bash
# Port'u kullanan process bul
sudo lsof -i :9000
sudo lsof -i :9001

# Öldür
sudo kill -9 <PID>

# Veya farklı port kullan
/opt/minio server /data/minio --console-address :9002 --address :9010
```

### Buckets görünmüyor

```bash
# MinIO user'ının data klasöre erişimi var mı?
sudo ls -la /data/minio

# Permissions fix
sudo chown -R minio:minio /data/minio
```

---

## 📋 One-Line Installer (Automated)

```bash
#!/bin/bash
set -e

echo "Installing MinIO..."
sudo rm -f /opt/minio
cd /tmp && wget -q https://dl.min.io/server/minio/release/linux-amd64/minio
sudo mv minio /opt/minio && sudo chmod +x /opt/minio

mkdir -p /data/minio && chmod 700 /data/minio
sudo useradd -r -s /sbin/nologin minio 2>/dev/null || true
sudo chown -R minio:minio /data/minio

# Service
sudo tee /etc/systemd/system/minio.service > /dev/null <<'EOF'
[Unit]
Description=MinIO
After=network.target

[Service]
Type=notify
User=minio
ExecStart=/opt/minio server /data/minio --console-address :9001
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/default/minio > /dev/null <<'EOF'
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
EOF

sudo systemctl daemon-reload
sudo systemctl enable minio
sudo systemctl start minio

echo "✓ MinIO started"
echo "Console: http://10.144.100.204:9001"
echo "API:     http://10.144.100.204:9000"
```

Kaydet:
```bash
nano install-minio.sh
chmod +x install-minio.sh
sudo ./install-minio.sh
```

---

## ✅ Checklist

- [ ] Binary indirildi & executable
- [ ] `/data/minio` klasörü oluşturuldu
- [ ] Systemd service yapılandırıldı
- [ ] MinIO başlatıldı (`systemctl status minio`)
- [ ] Console erişilebilir (http://10.144.100.204:9001)
- [ ] Buckets oluşturuldu: `report-uploads`, `report-snapshots`
- [ ] Access Key oluşturuldu
- [ ] Python SDK testi geçti
- [ ] `.env` dosyasında credentials set

**Done! 🎉**
