#!/bin/bash
# MinIO Standalone Installer for Linux
# Usage: chmod +x install-minio-linux.sh && sudo ./install-minio-linux.sh

set -e

echo "════════════════════════════════════════════════════════════"
echo "  MinIO Standalone Installer (Linux)"
echo "════════════════════════════════════════════════════════════"
echo ""

# Check if root
if [ "$EUID" -ne 0 ]; then
  echo "❌ This script requires sudo"
  exit 1
fi

# Download MinIO
echo "▶ Downloading MinIO binary..."
rm -f /tmp/minio
cd /tmp

# Try x86_64 first
if wget -q https://dl.min.io/server/minio/release/linux-amd64/minio 2>/dev/null; then
  echo "✓ Downloaded linux-amd64"
elif wget -q https://dl.min.io/server/minio/release/linux-amd64-musl/minio 2>/dev/null; then
  echo "✓ Downloaded linux-amd64-musl (fallback)"
else
  echo "❌ Failed to download MinIO"
  exit 1
fi

# Verify binary
if ! file /tmp/minio | grep -q "ELF"; then
  echo "❌ Binary is not valid ELF executable"
  exit 1
fi
echo "✓ Binary valid"

# Install
echo "▶ Installing MinIO to /opt..."
rm -f /opt/minio
mv /tmp/minio /opt/minio
chmod +x /opt/minio
chown root:root /opt/minio

# Test
/opt/minio --version
echo "✓ MinIO installed"

# Create data directory
echo "▶ Creating data directory..."
mkdir -p /data/minio
chmod 700 /data/minio

# Create minio user
echo "▶ Creating minio user..."
useradd -r -s /sbin/nologin minio 2>/dev/null || true
chown -R minio:minio /data/minio
echo "✓ User created"

# Create systemd service
echo "▶ Setting up systemd service..."
tee /etc/systemd/system/minio.service > /dev/null <<'EOF'
[Unit]
Description=MinIO Object Storage
Documentation=https://docs.min.io
Wants=network-online.target
After=network-online.target

[Service]
Type=notify
User=minio
Group=minio
ProtectProcessNoaccess=true
ProtectSystem=full
LimitNOFILE=65536
ExecStart=/opt/minio server /data/minio --console-address :9001
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=minio

[Install]
WantedBy=multi-user.target
EOF
echo "✓ Service file created"

# Create default config
echo "▶ Setting up default credentials..."
tee /etc/default/minio > /dev/null <<'EOF'
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
EOF
chmod 600 /etc/default/minio
echo "✓ Default config set"

# Enable & start
echo "▶ Starting MinIO service..."
systemctl daemon-reload
systemctl enable minio
systemctl start minio

# Wait for startup
sleep 3

# Check status
if systemctl is-active --quiet minio; then
  echo "✓ MinIO service running"
else
  echo "❌ MinIO service failed to start"
  journalctl -u minio -n 20
  exit 1
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "✅ MinIO Installation Complete!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "📍 Console:  http://10.144.100.204:9001"
echo "📍 API:      http://10.144.100.204:9000"
echo ""
echo "🔐 Default Credentials:"
echo "   Username: minioadmin"
echo "   Password: minioadmin"
echo ""
echo "📋 Next Steps:"
echo "   1. Open http://10.144.100.204:9001 in browser"
echo "   2. Create buckets: 'report-uploads', 'report-snapshots'"
echo "   3. Create access key (Access Keys menu)"
echo "   4. Update .env with credentials"
echo ""
echo "📖 See: MINIO-LINUX-QUICKSTART.md"
echo "════════════════════════════════════════════════════════════"
