#!/bin/bash

# Advanced Wkhtmltopdf fix for macOS
# This script addresses the specific memory and subprocess issues on macOS

echo "🔧 Advanced Wkhtmltopdf Memory Fix for macOS"
echo "=============================================="

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ This script is designed for macOS only"
    exit 1
fi

# 1. Check current system resources
echo "📊 Checking system resources..."
echo "Available memory: $(vm_stat | grep 'Pages free' | awk '{print $3}' | sed 's/\.//') pages"
echo "File descriptors limit: $(ulimit -n)"
echo "Process limit: $(ulimit -u)"

# 2. Install/Update Homebrew if not present
if ! command -v brew &> /dev/null; then
    echo "🍺 Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# 3. Install required dependencies
echo "📦 Installing dependencies..."
brew install wkhtmltopdf
brew install psutil 2>/dev/null || pip3 install psutil

# 4. Create optimized wkhtmltopdf wrapper
echo "⚙️ Creating optimized wkhtmltopdf wrapper..."
cat > /usr/local/bin/wkhtmltopdf-optimized << 'EOF'
#!/bin/bash

# Optimized wkhtmltopdf wrapper for macOS
# Handles memory and subprocess limits

# Set memory and process limits
ulimit -v 2147483648  # 2GB virtual memory
ulimit -n 10000       # 10,000 file descriptors
ulimit -u 2048        # 2,048 processes

# Set environment variables for better performance
export WKHTMLTOPDF_CMD=/usr/local/bin/wkhtmltopdf
export WKHTMLTOIMAGE_CMD=/usr/local/bin/wkhtmltoimage

# Optimized arguments for macOS
OPTIMIZED_ARGS=(
    --disable-local-file-access
    --quiet
    --no-pdf-compression
    --disable-smart-shrinking
    --print-media-type
    --no-stop-slow-scripts
    --javascript-delay 3000
    --timeout 300
    --memory-limit 2147483648
    --disable-plugins
    --disable-javascript
    --load-error-handling ignore
    --load-media-error-handling ignore
    --no-images
    --disable-external-links
    --disable-forms
    --disable-web-security
    --disable-features VizDisplayCompositor
)

# Execute with optimized settings
exec /usr/local/bin/wkhtmltopdf "${OPTIMIZED_ARGS[@]}" "$@"
EOF

chmod +x /usr/local/bin/wkhtmltopdf-optimized

# 5. Create system configuration
echo "🔧 Configuring system limits..."
sudo tee /etc/launchd.conf > /dev/null << EOF
limit maxfiles 10000 10000
limit maxproc 2048 2048
EOF

# 6. Create launchd configuration for Odoo
echo "🚀 Creating launchd configuration..."
sudo tee /Library/LaunchDaemons/com.odoo.wkhtmltopdf.plist > /dev/null << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.odoo.wkhtmltopdf</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/wkhtmltopdf-optimized</string>
    </array>
    <key>SoftResourceLimits</key>
    <dict>
        <key>NumberOfFiles</key>
        <integer>10000</integer>
        <key>NumberOfProcesses</key>
        <integer>2048</integer>
    </dict>
    <key>HardResourceLimits</key>
    <dict>
        <key>NumberOfFiles</key>
        <integer>10000</integer>
        <key>NumberOfProcesses</key>
        <integer>2048</integer>
    </dict>
</dict>
</plist>
EOF

# 7. Create Python script for dynamic memory management
echo "🐍 Creating Python memory management script..."
cat > /usr/local/bin/odoo_memory_manager.py << 'EOF'
#!/usr/bin/env python3
"""
Odoo Memory Manager for macOS
Dynamically adjusts memory limits based on system resources
"""

import psutil
import os
import sys

def get_optimal_memory_limit():
    """Calculate optimal memory limit based on available system memory"""
    memory = psutil.virtual_memory()
    available_gb = memory.available / (1024**3)
    
    if available_gb > 8:
        return "4294967296"  # 4GB
    elif available_gb > 4:
        return "2147483648"   # 2GB
    elif available_gb > 2:
        return "1073741824"   # 1GB
    else:
        return "536870912"    # 512MB

def get_optimal_timeout():
    """Calculate optimal timeout based on system load"""
    load_avg = os.getloadavg()[0]
    cpu_count = psutil.cpu_count()
    
    if load_avg > cpu_count * 0.8:
        return "600"  # 10 minutes
    elif load_avg > cpu_count * 0.5:
        return "300"  # 5 minutes
    else:
        return "120"  # 2 minutes

if __name__ == "__main__":
    print(f"MEMORY_LIMIT={get_optimal_memory_limit()}")
    print(f"TIMEOUT={get_optimal_timeout()}")
EOF

chmod +x /usr/local/bin/odoo_memory_manager.py

# 8. Create Odoo configuration template
echo "📝 Creating Odoo configuration template..."
cat > /tmp/odoo_wkhtmltopdf.conf << EOF
# Wkhtmltopdf Configuration for Odoo
# Add these settings to your odoo.conf file

# Memory limits
limit_memory_hard = 4294967296
limit_memory_soft = 2147483648

# Worker configuration
workers = 4
max_cron_threads = 2

# Wkhtmltopdf settings
WKHTMLTOPDF_CMD = /usr/local/bin/wkhtmltopdf-optimized
WKHTMLTOIMAGE_CMD = /usr/local/bin/wkhtmltoimage

# Database settings
db_maxconn = 64
db_template = template0

# Logging
log_level = info
log_handler = :INFO
EOF

# 9. Create monitoring script
echo "📊 Creating system monitoring script..."
cat > /usr/local/bin/monitor_odoo_memory.sh << 'EOF'
#!/bin/bash

# Monitor Odoo memory usage and wkhtmltopdf processes
echo "🔍 Odoo Memory Monitor"
echo "======================"

echo "📊 System Memory:"
vm_stat | grep -E "(Pages free|Pages active|Pages inactive)"

echo ""
echo "🔍 Wkhtmltopdf Processes:"
ps aux | grep wkhtmltopdf | grep -v grep

echo ""
echo "📈 Odoo Processes:"
ps aux | grep odoo | grep -v grep

echo ""
echo "💾 Memory Usage:"
top -l 1 | grep -E "(PhysMem|VM)"

echo ""
echo "🔧 File Descriptors:"
lsof -p $(pgrep -f odoo) | wc -l
EOF

chmod +x /usr/local/bin/monitor_odoo_memory.sh

# 10. Create test script
echo "🧪 Creating test script..."
cat > /usr/local/bin/test_wkhtmltopdf.sh << 'EOF'
#!/bin/bash

# Test wkhtmltopdf functionality
echo "🧪 Testing Wkhtmltopdf Configuration"
echo "===================================="

# Test basic functionality
echo "1. Testing basic wkhtmltopdf..."
echo "<html><body><h1>Test</h1></body></html>" | /usr/local/bin/wkhtmltopdf-optimized - - > /tmp/test_basic.pdf
if [ $? -eq 0 ]; then
    echo "✅ Basic test passed"
else
    echo "❌ Basic test failed"
fi

# Test with memory limit
echo "2. Testing with memory limit..."
echo "<html><body><h1>Memory Test</h1><p>This is a test document for memory management.</p></body></html>" | /usr/local/bin/wkhtmltopdf-optimized --memory-limit 1073741824 - - > /tmp/test_memory.pdf
if [ $? -eq 0 ]; then
    echo "✅ Memory test passed"
else
    echo "❌ Memory test failed"
fi

# Test timeout
echo "3. Testing timeout..."
timeout 10s /usr/local/bin/wkhtmltopdf-optimized --timeout 5 - - < /dev/null > /tmp/test_timeout.pdf 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ Timeout test passed"
else
    echo "❌ Timeout test failed"
fi

echo ""
echo "📁 Test files created in /tmp/"
ls -la /tmp/test_*.pdf
EOF

chmod +x /usr/local/bin/test_wkhtmltopdf.sh

# 11. Final configuration
echo "🎯 Final configuration..."

# Set environment variables
export WKHTMLTOPDF_CMD=/usr/local/bin/wkhtmltopdf-optimized
export WKHTMLTOIMAGE_CMD=/usr/local/bin/wkhtmltoimage

# Add to shell profile
echo "" >> ~/.zshrc
echo "# Odoo Wkhtmltopdf Configuration" >> ~/.zshrc
echo "export WKHTMLTOPDF_CMD=/usr/local/bin/wkhtmltopdf-optimized" >> ~/.zshrc
echo "export WKHTMLTOIMAGE_CMD=/usr/local/bin/wkhtmltoimage" >> ~/.zshrc

echo ""
echo "✅ Advanced Wkhtmltopdf fix completed!"
echo ""
echo "📋 Next steps:"
echo "1. Add the configuration from /tmp/odoo_wkhtmltopdf.conf to your odoo.conf"
echo "2. Restart your Odoo service"
echo "3. Run the test: /usr/local/bin/test_wkhtmltopdf.sh"
echo "4. Monitor with: /usr/local/bin/monitor_odoo_memory.sh"
echo ""
echo "🔧 Configuration file location: /tmp/odoo_wkhtmltopdf.conf"
echo "🧪 Test script: /usr/local/bin/test_wkhtmltopdf.sh"
echo "📊 Monitor script: /usr/local/bin/monitor_odoo_memory.sh"
