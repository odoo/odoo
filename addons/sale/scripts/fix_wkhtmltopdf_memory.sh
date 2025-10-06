#!/bin/bash

# Script to fix Wkhtmltopdf memory issues in Odoo 19
# This script should be run as root or with sudo privileges

echo "Fixing Wkhtmltopdf memory issues for Odoo 19..."

# 1. Increase system limits
echo "Setting system limits..."

# Increase file descriptor limit
echo "* soft nofile 10000" >> /etc/security/limits.conf
echo "* hard nofile 10000" >> /etc/security/limits.conf

# Increase memory limits
echo "vm.max_map_count=262144" >> /etc/sysctl.conf
echo "vm.swappiness=10" >> /etc/sysctl.conf

# Apply sysctl changes
sysctl -p

# 2. Install or update wkhtmltopdf
echo "Installing/updating wkhtmltopdf..."

# For Ubuntu/Debian
if command -v apt-get &> /dev/null; then
    # Remove old version if exists
    apt-get remove -y wkhtmltopdf 2>/dev/null || true
    
    # Install dependencies
    apt-get update
    apt-get install -y wget
    
    # Download and install patched version
    wget https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox_0.12.6-1.focal_amd64.deb
    dpkg -i wkhtmltox_0.12.6-1.focal_amd64.deb || apt-get install -f -y
    rm wkhtmltox_0.12.6-1.focal_amd64.deb
fi

# For CentOS/RHEL
if command -v yum &> /dev/null; then
    yum install -y wget
    wget https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox-0.12.6-1.centos7.x86_64.rpm
    yum localinstall -y wkhtmltox-0.12.6-1.centos7.x86_64.rpm
    rm wkhtmltox-0.12.6-1.centos7.x86_64.rpm
fi

# 3. Create systemd override for Odoo service (if using systemd)
if systemctl is-active --quiet odoo 2>/dev/null; then
    echo "Creating systemd override for Odoo service..."
    mkdir -p /etc/systemd/system/odoo.service.d/
    cat > /etc/systemd/system/odoo.service.d/override.conf << EOF
[Service]
LimitNOFILE=10000
LimitNPROC=4096
MemoryLimit=4G
EOF
    systemctl daemon-reload
    systemctl restart odoo
fi

# 4. Set environment variables for current session
export WKHTMLTOPDF_CMD=/usr/local/bin/wkhtmltopdf
export WKHTMLTOIMAGE_CMD=/usr/local/bin/wkhtmltoimage

# 5. Create wrapper script for wkhtmltopdf with memory management
cat > /usr/local/bin/wkhtmltopdf-wrapper << 'EOF'
#!/bin/bash
# Wrapper script for wkhtmltopdf with memory management

# Set memory limits
ulimit -v 2684354560  # 2.5GB virtual memory
ulimit -n 10000       # 10000 file descriptors

# Run wkhtmltopdf with optimized parameters
exec /usr/local/bin/wkhtmltopdf \
    --disable-local-file-access \
    --quiet \
    --no-pdf-compression \
    --disable-smart-shrinking \
    --print-media-type \
    --no-stop-slow-scripts \
    --javascript-delay 1000 \
    --timeout 300 \
    "$@"
EOF

chmod +x /usr/local/bin/wkhtmltopdf-wrapper

# 6. Create symlink to use wrapper
ln -sf /usr/local/bin/wkhtmltopdf-wrapper /usr/local/bin/wkhtmltopdf-optimized

echo "Wkhtmltopdf memory fix completed!"
echo "Please restart your Odoo service and test the email functionality."
echo ""
echo "To use the optimized version, set in your Odoo configuration:"
echo "WKHTMLTOPDF_CMD=/usr/local/bin/wkhtmltopdf-optimized"
