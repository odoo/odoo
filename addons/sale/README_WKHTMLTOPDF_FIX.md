# Wkhtmltopdf Memory Fix for Odoo 19 Sale Module

This document describes the fixes implemented to resolve the "Wkhtmltopdf failed (error code: -11). Memory limit too low or maximum file number of subprocess reached" error in Odoo 19.

## Problem Description

The error occurs when trying to send emails with PDF attachments in the sale.order model. This is typically caused by:

1. **Memory limitations**: Wkhtmltopdf process exceeds available memory
2. **File descriptor limits**: System runs out of available file descriptors
3. **Subprocess limits**: Too many concurrent processes

## Changes Made

### 1. Added Missing Mail Compose Message Handler

**File**: `wizard/mail_compose_message.py`
- Restored the missing `mail_compose_message.py` file that was present in Odoo 18 but missing in Odoo 19
- Handles email composition for sale orders with proper context management

### 2. Enhanced Report Generation with Memory Management

**File**: `models/ir_actions_report.py`
- Override `_build_wkhtmltopdf_args()` to add memory management options
- Override `_run_wkhtmltopdf()` to handle memory issues and subprocess limits
- Added timeout handling and better error messages
- Implemented temporary file usage to reduce memory consumption

### 3. Configuration Parameters

**File**: `data/ir_config_parameter_wkhtmltopdf.xml`
- Added system configuration parameters for Wkhtmltopdf optimization:
  - `report.wkhtmltopdf.memory_limit`: Set to 2.5GB (2684354560 bytes)
  - `report.wkhtmltopdf.max_file_descriptors`: Set to 10000
  - `report.wkhtmltopdf.timeout`: Set to 300 seconds
  - `report.wkhtmltopdf.quiet`: Enable quiet mode
  - `report.wkhtmltopdf.disable-local-file-access`: Security setting

### 4. System Configuration Script

**File**: `scripts/fix_wkhtmltopdf_memory.sh`
- Automated script to fix system-level issues
- Increases file descriptor limits
- Installs/updates Wkhtmltopdf to patched version
- Creates optimized wrapper script
- Configures systemd overrides for Odoo service

## Installation Instructions

### 1. Apply the Code Changes

The following files have been created/modified:
- `wizard/mail_compose_message.py` (new)
- `models/ir_actions_report.py` (new)
- `data/ir_config_parameter_wkhtmltopdf.xml` (new)
- `wizard/__init__.py` (updated)
- `__manifest__.py` (updated)

### 2. Run System Configuration Script

```bash
# Make the script executable
chmod +x /Users/nguyenthi/NguyenThi/odoo_dev/odoo/addons/sale/scripts/fix_wkhtmltopdf_memory.sh

# Run as root or with sudo
sudo /Users/nguyenthi/NguyenThi/odoo_dev/odoo/addons/sale/scripts/fix_wkhtmltopdf_memory.sh
```

### 3. Update Odoo Configuration

Add the following to your `odoo.conf` file:

```ini
# Wkhtmltopdf configuration
limit_memory_hard = 2684354560
limit_memory_soft = 2147483648
workers = 4
max_cron_threads = 2

# Optional: Use optimized wkhtmltopdf wrapper
# WKHTMLTOPDF_CMD = /usr/local/bin/wkhtmltopdf-optimized
```

### 4. Restart Services

```bash
# Restart Odoo service
sudo systemctl restart odoo

# Or if using different service name
sudo systemctl restart odoo19
```

## Verification

### 1. Check Wkhtmltopdf Installation

```bash
wkhtmltopdf --version
# Should show version 0.12.6 or higher
```

### 2. Test Email Functionality

1. Go to Sales > Orders
2. Create or open a sale order
3. Click "Send by Email"
4. Verify that the email is sent without errors

### 3. Check System Limits

```bash
# Check file descriptor limits
ulimit -n
# Should show 10000 or higher

# Check memory limits
ulimit -v
# Should show appropriate memory limit
```

## Troubleshooting

### If the error persists:

1. **Check system resources**:
   ```bash
   free -h
   df -h
   ```

2. **Monitor system limits**:
   ```bash
   cat /proc/sys/fs/file-max
   cat /proc/sys/vm/max_map_count
   ```

3. **Check Odoo logs**:
   ```bash
   tail -f /var/log/odoo/odoo.log
   ```

4. **Verify Wkhtmltopdf configuration**:
   ```bash
   /usr/local/bin/wkhtmltopdf-optimized --version
   ```

### Manual Configuration

If the automated script doesn't work, you can manually configure:

1. **Increase file descriptors**:
   ```bash
   echo "* soft nofile 10000" >> /etc/security/limits.conf
   echo "* hard nofile 10000" >> /etc/security/limits.conf
   ```

2. **Set memory limits**:
   ```bash
   echo "vm.max_map_count=262144" >> /etc/sysctl.conf
   sysctl -p
   ```

3. **Install patched Wkhtmltopdf**:
   ```bash
   wget https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox_0.12.6-1.focal_amd64.deb
   sudo dpkg -i wkhtmltox_0.12.6-1.focal_amd64.deb
   ```

## Performance Optimization

The implemented solution includes several performance optimizations:

1. **Memory Management**: Uses temporary files instead of keeping everything in memory
2. **Resource Limits**: Sets appropriate limits for file descriptors and memory
3. **Timeout Handling**: Prevents hanging processes
4. **Error Handling**: Provides clear error messages for different failure scenarios
5. **Fallback Mechanism**: Falls back to original method if enhanced method fails

## Compatibility

- **Odoo Version**: 19.0
- **Python Version**: 3.8+
- **Wkhtmltopdf Version**: 0.12.6+
- **Operating System**: Linux (Ubuntu, CentOS, RHEL)

## Support

If you continue to experience issues after applying these fixes, please check:

1. System resources (RAM, disk space)
2. Odoo configuration settings
3. Wkhtmltopdf installation and version
4. System limits and permissions

The solution is designed to be backward compatible and should not affect existing functionality.
