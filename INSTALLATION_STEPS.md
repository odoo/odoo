# PostgreSQL Installation - Step by Step Guide

## Step 1: Download PostgreSQL ✅

The download should have started. If not:
1. Go to: https://www.enterprisedb.com/downloads/postgres-postgresql-downloads
2. Find PostgreSQL 16.11 in the table
3. Click the Windows icon (second to last column)
4. The installer file (e.g., `postgresql-16.11-1-windows-x64.exe`) will download

**File location**: Usually in your `Downloads` folder

---

## Step 2: Run the Installer

1. **Find the downloaded file** in your Downloads folder
   - File name: `postgresql-16.11-1-windows-x64.exe` (or similar)
2. **Double-click** the installer to run it
3. If Windows asks for permission, click **"Yes"**

---

## Step 3: Installation Wizard Steps

### Screen 1: Welcome
- Click **"Next"**

### Screen 2: Installation Directory
- Keep default: `C:\Program Files\PostgreSQL\16`
- Click **"Next"**

### Screen 3: Select Components
- ✅ PostgreSQL Server (checked)
- ✅ pgAdmin 4 (checked) - GUI tool for managing databases
- ✅ Stack Builder (checked) - Optional, can uncheck
- ✅ Command Line Tools (checked) - **IMPORTANT: Keep this checked**
- Click **"Next"**

### Screen 4: Data Directory
- Keep default: `C:\Program Files\PostgreSQL\16\data`
- Click **"Next"**

### Screen 5: Password ⚠️ **IMPORTANT**
- **Enter a password** for the `postgres` superuser
- **Remember this password!** You'll need it later
- Example: Use something like `postgres123` or `admin123` (for development)
- Click **"Next"**

### Screen 6: Port
- Keep default: **5432**
- Click **"Next"**

### Screen 7: Advanced Options (Locale)
- Keep default locale
- Click **"Next"**

### Screen 8: Pre Installation Summary
- Review the settings
- Click **"Next"**

### Screen 9: Ready to Install
- Click **"Next"** to begin installation
- Wait for installation to complete (this may take a few minutes)

### Screen 10: Completing the PostgreSQL Setup
- ✅ Uncheck "Launch Stack Builder" (we don't need it)
- Click **"Finish"**

---

## Step 4: Verify Installation

After installation, let me know and I'll help you:
1. Verify PostgreSQL is running
2. Create the Odoo database user
3. Test the connection

---

## What to Do Next

Once installation is complete, come back here and I'll help you with:
- ✅ Step 2: Creating the Odoo database user
- ✅ Step 3: Testing the connection

**Tell me when the installation is finished!**
