# Odoo 17 -> 18 Upgrade + Windows 11 Dev Setup + IONOS VPS Deployment

Complete step-by-step guide for upgrading this repository from Odoo 17 Community
to Odoo 18 Community, setting up a VS Code development environment on Windows 11,
and deploying to an IONOS VPS.

---

## Table of Contents

1. [Prerequisites & Downloads](#1-prerequisites--downloads)
2. [Upgrade the Repository to Odoo 18](#2-upgrade-the-repository-to-odoo-18)
3. [Install Python 3.12 on Windows 11](#3-install-python-312-on-windows-11)
4. [Install PostgreSQL 16 on Windows 11](#4-install-postgresql-16-on-windows-11)
5. [Set Up the Python Virtual Environment](#5-set-up-the-python-virtual-environment)
6. [Install wkhtmltopdf](#6-install-wkhtmltopdf)
7. [Configure VS Code for Odoo Development](#7-configure-vs-code-for-odoo-development)
8. [Run Odoo Locally for the First Time](#8-run-odoo-locally-for-the-first-time)
9. [Adding Custom / Third-Party Modules](#9-adding-custom--third-party-modules)
10. [Migrating Custom Modules from v17 to v18](#10-migrating-custom-modules-from-v17-to-v18)
11. [Deploy to IONOS VPS](#11-deploy-to-ionos-vps)
12. [Key Breaking Changes: Odoo 17 vs 18](#12-key-breaking-changes-odoo-17-vs-18)

---

## 1. Prerequisites & Downloads

Download and install these on your Windows 11 machine:

| Software | Version | Download Link |
|----------|---------|---------------|
| **Git for Windows** | Latest | https://git-scm.com/download/win |
| **Python** | 3.12.x | https://www.python.org/downloads/ |
| **PostgreSQL** | 16.x | https://www.enterprisedb.com/downloads/postgres-postgresql-downloads |
| **VS Code** | Latest | https://code.visualstudio.com/download |
| **wkhtmltopdf** | 0.12.6.1 | https://github.com/wkhtmltopdf/packaging/releases/tag/0.12.6.1-3 |
| **Node.js** | 20 LTS | https://nodejs.org/ (needed for rtlcss) |

---

## 2. Upgrade the Repository to Odoo 18

Your current repo (`ovoco`) is on Odoo 17.0. Here's how to upgrade to 18:

### Option A: Replace with Official Odoo 18 Source (Recommended for Clean Upgrade)

```powershell
# 1. Open PowerShell and navigate to your projects folder
cd C:\Projects  # or wherever you keep your code

# 2. Rename your current repo as backup
Rename-Item ovoco ovoco-v17-backup

# 3. Clone the official Odoo 18 Community source
git clone https://github.com/odoo/odoo.git --single-branch -b 18.0 --depth 1 ovoco

# 4. Copy over your custom_addons from the old repo (if any)
Copy-Item -Recurse ovoco-v17-backup\custom_addons\* ovoco\custom_addons\

# 5. Copy the VS Code and deploy configs
Copy-Item -Recurse ovoco-v17-backup\.vscode ovoco\.vscode
Copy-Item -Recurse ovoco-v17-backup\deploy ovoco\deploy
Copy-Item ovoco-v17-backup\odoo.conf ovoco\odoo.conf
```

### Option B: Add Odoo 18 as Upstream Remote (Preserves Git History)

```powershell
# 1. Navigate to your repo
cd C:\Projects\ovoco

# 2. Add the official Odoo repo as a remote
git remote add upstream https://github.com/odoo/odoo.git

# 3. Fetch the 18.0 branch
git fetch upstream 18.0

# 4. Create a new branch based on Odoo 18
git checkout -b 18.0 upstream/18.0

# 5. Your custom_addons, .vscode, and deploy folders will already be here
#    since they're committed to the repo
```

### After Either Option

```powershell
# Verify you're on Odoo 18
python -c "import odoo; print(odoo.release.version)"
# Should output: 18.0
```

---

## 3. Install Python 3.12 on Windows 11

1. Download Python 3.12.x from https://www.python.org/downloads/
2. Run the installer
3. **CRITICAL**: Check the box **"Add Python 3.12 to PATH"** at the bottom
4. Click **"Customize installation"**
5. Check all Optional Features, click Next
6. Check **"Install for all users"** and note the install path (e.g., `C:\Python312`)
7. Click Install

### Verify Installation

```powershell
python --version
# Should show: Python 3.12.x

pip --version
# Should show pip with Python 3.12
```

---

## 4. Install PostgreSQL 16 on Windows 11

1. Download PostgreSQL 16 from https://www.enterprisedb.com/downloads/postgres-postgresql-downloads
2. Run the installer
3. Set a password for the `postgres` superuser (remember this!)
4. Keep the default port **5432**
5. Complete the installation (you can skip Stack Builder)

### Create the Odoo Database User

Open **pgAdmin 4** (installed with PostgreSQL) or use the command line:

```powershell
# Open PowerShell as Administrator
# Navigate to PostgreSQL bin directory
cd "C:\Program Files\PostgreSQL\16\bin"

# Create the odoo user with permission to create databases
.\createuser.exe --createdb --pwprompt --username=postgres odoo
# When prompted, enter password: odoo (or your choice)
# When asked for the postgres user password, enter what you set during install
```

### Verify Connection

```powershell
.\psql.exe -U odoo -d postgres -c "SELECT version();"
```

---

## 5. Set Up the Python Virtual Environment

```powershell
# 1. Navigate to the Odoo project folder
cd C:\Projects\ovoco

# 2. Create a virtual environment
python -m venv venv

# 3. Activate the virtual environment
.\venv\Scripts\Activate.ps1
# If you get an execution policy error, run first:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 4. Upgrade pip
python -m pip install --upgrade pip setuptools wheel

# 5. Install Odoo dependencies
pip install -r requirements.txt

# 6. Install development tools
pip install pylint pylint-odoo python-dotenv debugpy watchdog

# 7. Install rtlcss (for right-to-left language support)
npm install -g rtlcss
```

### If You Get Build Errors on Windows

Some packages like `psycopg2` or `python-ldap` may fail to compile on Windows.
Use pre-built wheels instead:

```powershell
# Use psycopg2-binary instead of psycopg2
pip install psycopg2-binary

# For python-ldap on Windows, skip it (only needed for LDAP auth)
# Or download a pre-built wheel from:
# https://www.lfd.uci.edu/~gohlke/pythonlibs/
```

---

## 6. Install wkhtmltopdf

1. Download **wkhtmltox-0.12.6.1** for Windows from:
   https://github.com/wkhtmltopdf/packaging/releases/tag/0.12.6.1-3
2. Run the installer (default path: `C:\Program Files\wkhtmltopdf`)
3. Add to PATH:
   - Open **System Properties** > **Environment Variables**
   - Under **System variables**, find `Path`, click Edit
   - Add: `C:\Program Files\wkhtmltopdf\bin`
4. Verify:

```powershell
wkhtmltopdf --version
# Should show: wkhtmltopdf 0.12.6.1
```

---

## 7. Configure VS Code for Odoo Development

### Install VS Code Extensions

The repo includes `.vscode/extensions.json` which will prompt you to install
recommended extensions when you open the project. You can also install them manually:

1. Open VS Code
2. Open the Extensions panel (`Ctrl+Shift+X`)
3. Install these extensions:
   - **Python** (ms-python.python)
   - **Debugpy** (ms-python.debugpy) - Python debugger
   - **Pylint** (ms-python.pylint) - Python linting
   - **Odoo IDE** (trinhanhngoc.vscode-odoo) - Odoo framework integration
   - **XML** (redhat.vscode-xml) - XML editing for Odoo views
   - **ESLint** (dbaeumer.vscode-eslint) - JavaScript linting
   - **GitLens** (eamodio.gitlens) - Git history and blame

### Open the Project

```powershell
cd C:\Projects\ovoco
code .
```

### Select Python Interpreter

1. Press `Ctrl+Shift+P` > "Python: Select Interpreter"
2. Choose the one from your virtual environment: `.\venv\Scripts\python.exe`

### VS Code Configurations Already Included

The repo already includes these configuration files:

- **`.vscode/settings.json`** - Python paths, linting rules, editor settings
- **`.vscode/launch.json`** - Debug configurations:
  - **"Odoo 18: Start Server"** - Normal server start with auto-reload
  - **"Odoo 18: Start (with debugger)"** - Full debug mode with breakpoints
  - **"Odoo 18: Update Module"** - Update a specific module (will prompt for name)
  - **"Odoo 18: Scaffold New Module"** - Create a new module skeleton in custom_addons
- **`.vscode/extensions.json`** - Recommended extensions list

### Using the Debugger

1. Set breakpoints in any Python file by clicking the left gutter
2. Press `F5` or go to **Run > Start Debugging**
3. Select **"Odoo 18: Start (with debugger)"**
4. Odoo will start and stop at your breakpoints
5. Use the Debug Console to inspect variables

---

## 8. Run Odoo Locally for the First Time

### Update the Configuration

Copy and edit the config file in the project root:

```powershell
# Copy the example config
copy odoo.conf.example odoo.conf
```

Then update:

```ini
[options]
db_host = localhost
db_port = 5432
db_user = odoo
db_password = odoo    ; <-- the password you set in step 4
addons_path = addons,custom_addons,odoo/addons
```

### Start Odoo

**Method 1: From VS Code (Recommended)**
- Press `F5` and select "Odoo 18: Start Server"

**Method 2: From Terminal**
```powershell
# Make sure venv is activated
.\venv\Scripts\Activate.ps1

# Start Odoo
python odoo-bin -c odoo.conf --dev=reload,xml
```

### Access Odoo

1. Open your browser to: **http://localhost:8069**
2. You'll see the **Database Manager** page
3. Create a new database:
   - **Master Password**: `admin` (from odoo.conf)
   - **Database Name**: `odoo18dev`
   - **Email**: your email
   - **Password**: your choice
   - **Language**: English
   - **Country**: your country
   - Check **"Demo data"** if you want sample data for testing
4. Click **Create Database** and wait for setup to complete
5. You'll be logged into your fresh Odoo 18 instance

---

## 9. Adding Custom / Third-Party Modules

A `custom_addons/` folder has been created in the project root. This is where
all third-party and custom modules go.

### To Add a Module

1. **Download or clone** the module into `custom_addons/`:

```powershell
# Example: clone an OCA module
cd C:\Projects\ovoco\custom_addons
git clone https://github.com/OCA/some-module.git -b 18.0 some_module
```

2. **Or copy** the module folder directly:
   - Simply drag and drop the module folder into `C:\Projects\ovoco\custom_addons\`

3. **Restart Odoo** and update the apps list:
   - Go to **Apps** menu
   - Click **Update Apps List** (you may need to enable Developer Mode first)
   - Search for your module and click **Install**

### Enable Developer Mode

Go to **Settings** > scroll to the bottom > click **Activate the developer mode**

Or navigate directly to: `http://localhost:8069/web?debug=1`

---

## 10. Migrating Custom Modules from v17 to v18

If your custom modules were built for Odoo 17, you need to update them for v18.

### Automated Migration Tool

The OCA provides a module migrator:

```powershell
pip install odoo-module-migrator

# Run the migrator on your custom module
odoo-module-migrate --directory C:\Projects\ovoco\custom_addons\your_module --target-version 18.0
```

### Manual Changes Required

1. **Update `__manifest__.py`**:
   ```python
   # Change version from 17.0.x.x.x to 18.0.x.x.x
   'version': '18.0.1.0.0',
   ```

2. **Replace deprecated methods**:
   - `name_get()` -> use `display_name` field
   - `_read_group()` has a new signature
   - `group_operator` -> `aggregator` in field definitions
   - `inselect` operator removed -> use `in` with Query objects

3. **Update OWL components** (if you have JavaScript):
   - Odoo 18 uses OWL 2.x with some API changes

4. **Test thoroughly**: Install in your dev environment and check for errors in the log

### Quick Checklist for Each Custom Module

- [ ] Update version in `__manifest__.py` to `18.0.x.x.x`
- [ ] Replace `name_get()` with `_compute_display_name()`
- [ ] Update `_read_group()` calls to new signature
- [ ] Replace `group_operator` with `aggregator`
- [ ] Remove any use of `inselect` operator
- [ ] Test installation on Odoo 18
- [ ] Test all module functionality
- [ ] Check Odoo server logs for deprecation warnings

---

## 11. Deploy to IONOS VPS

### Prerequisites on the VPS

- Ubuntu 22.04/24.04 or Debian 12 (recommended)
- SSH access to your IONOS VPS
- Docker and Docker Compose installed

### Step 1: Install Docker on the VPS

```bash
# SSH into your VPS
ssh root@your-vps-ip

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose plugin
apt-get install docker-compose-plugin

# Verify
docker --version
docker compose version
```

### Step 2: Push Your Code to the VPS

**Option A: Push via Git (Recommended)**

```bash
# On the VPS, clone your repo
cd /opt
git clone https://github.com/lindyjan/ovoco.git
cd ovoco
git checkout 18.0   # or your branch
```

**Option B: Copy via SCP**

```powershell
# From your Windows machine
scp -r C:\Projects\ovoco root@your-vps-ip:/opt/ovoco
```

### Step 3: Configure Environment Variables

```bash
cd /opt/ovoco/deploy

# Create .env from the example
cp .env.example .env

# Edit with a strong password
nano .env
# Change POSTGRES_PASSWORD=your_strong_password_here
```

### Step 4: Update the Server Config

```bash
nano /opt/ovoco/deploy/odoo-server.conf

# IMPORTANT: Update these values:
# admin_passwd = YOUR_STRONG_MASTER_PASSWORD
# db_password = same as POSTGRES_PASSWORD in .env
```

### Step 5: Build and Start

```bash
cd /opt/ovoco/deploy

# Build the Docker image
docker compose build

# Start the containers (detached)
docker compose up -d

# Check logs
docker compose logs -f odoo
```

### Step 6: Set Up Nginx Reverse Proxy (Recommended)

```bash
# Install Nginx
apt-get install nginx

# Create Odoo site config
nano /etc/nginx/sites-available/odoo
```

Add this configuration:

```nginx
upstream odoo {
    server 127.0.0.1:8069;
}

upstream odoo-chat {
    server 127.0.0.1:8072;
}

server {
    listen 80;
    server_name your-domain.com;

    # Redirect to HTTPS (uncomment after setting up SSL)
    # return 301 https://$server_name$request_uri;

    proxy_read_timeout 720s;
    proxy_connect_timeout 720s;
    proxy_send_timeout 720s;

    # Proxy headers
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Real-IP $remote_addr;

    # Log
    access_log /var/log/nginx/odoo.access.log;
    error_log /var/log/nginx/odoo.error.log;

    # Longpolling
    location /websocket {
        proxy_pass http://odoo-chat;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Odoo backend
    location / {
        proxy_redirect off;
        proxy_pass http://odoo;
    }

    # Common static
    location ~* /web/static/ {
        proxy_cache_valid 200 90m;
        proxy_buffering on;
        expires 864000;
        proxy_pass http://odoo;
    }

    # Gzip
    gzip_types text/css text/plain text/xml application/xml application/javascript application/json;
    gzip on;

    client_max_body_size 200m;
}
```

Enable the site:

```bash
ln -s /etc/nginx/sites-available/odoo /etc/nginx/sites-enabled/
rm /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx
```

### Step 7: Set Up SSL with Let's Encrypt

```bash
apt-get install certbot python3-certbot-nginx
certbot --nginx -d your-domain.com
# Follow the prompts
```

### Step 8: Access Your Odoo Instance

Navigate to `http://your-domain.com` (or `https://` after SSL setup)

### Maintenance Commands

```bash
# View logs
docker compose logs -f odoo

# Restart Odoo
docker compose restart odoo

# Stop everything
docker compose down

# Update Odoo (pull latest code and rebuild)
cd /opt/ovoco
git pull
cd deploy
docker compose build
docker compose up -d

# Backup database
docker compose exec db pg_dump -U odoo your_database > backup_$(date +%F).sql

# Restore database
docker compose exec -T db psql -U odoo your_database < backup_file.sql
```

---

## 12. Key Breaking Changes: Odoo 17 vs 18

| Change | Odoo 17 | Odoo 18 |
|--------|---------|---------|
| Name display | `name_get()` (deprecated) | `_compute_display_name()` |
| Read group | Old `_read_group()` signature | New `_read_group()` signature |
| Field attribute | `group_operator` | `aggregator` |
| Domain operator | `inselect` available | `inselect` removed, use `in` with Query |
| Name search | `name_search()` | `_search_display_name` |
| Access checks | Separate methods | Combined `check_access`, `has_access`, `_filtered_access` |
| Python version | 3.10+ | 3.10+ (3.12 recommended) |
| PostgreSQL | 12+ | 15+ recommended |
| OWL framework | OWL 2.x | OWL 2.x (updated components) |

### Sources

- [Odoo 18 ORM Changelog](https://www.odoo.com/documentation/18.0/developer/reference/backend/orm/changelog.html)
- [Odoo 18 Source Install Docs](https://www.odoo.com/documentation/18.0/administration/on_premise/source.html)
- [Odoo 18 Upgrade Docs](https://www.odoo.com/documentation/18.0/administration/upgrade.html)
- [OCA Module Migrator](https://github.com/OCA/odoo-module-migrator)
- [Odoo 18 Setup Guide](https://www.odoo.com/documentation/18.0/developer/tutorials/setup_guide.html)
