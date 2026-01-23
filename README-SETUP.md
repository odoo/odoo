# Odoo 14 Setup Summary - GitHub Codespace

## Status

Odoo 14 is now set up with Python 3.12 compatibility patches applied. Due to compatibility issues between Python 3.12 and Odoo 14, several bytecode opcodes needed to be added to `safe_eval.py`.

## Current Setup

### Configuration File (`/workspaces/odoo/odoo.conf`)
```
[options]
admin_passwd = admin
db_host = 127.0.0.1
db_port = 5433
db_user = odoo14
db_password = odoo14
db_maxconn = 64
addons_path = /workspaces/odoo/addons,/workspaces/odoo/odoo-custom-addons
logfile = /workspaces/odoo/odoo.log
log_level = debug
```

### Database
- PostgreSQL running in Docker container on port 5433
- Container: `odoo-postgres`
- User: `odoo14`
- Password: `odoo14`

### Custom HR Theme Module
- Location: `/workspaces/odoo/odoo-custom-addons/hr_custom_theme/`
- Module name: `hr_custom_theme`
- Provides custom styling for HR/Employee module

## Python 3.12 Compatibility Fixes Applied

The following opcodes were added to `/workspaces/odoo/odoo/tools/safe_eval.py`:

### `_CONST_OPCODES` (line 59)
- `RESUME` - added in Python 3.11
- `RETURN_CONST` - added in Python 3.12
- `COPY` - added in Python 3.11

### `_EXPR_OPCODES` (line 78)
- `RESUME` - added in Python 3.11

### `_SAFE_OPCODES` (line 94)
- `RESUME` - added in Python 3.11
- `PUSH_NULL` - added in Python 3.11
- `CALL` - added in Python 3.11
- `KW_NAMES` - added in Python 3.11

## How to Initialize and Run Odoo

### Method 1: Web Database Manager (Recommended)

1. Make sure no database exists:
```bash
docker exec odoo-postgres psql -U odoo14 -d postgres -c "DROP DATABASE IF EXISTS odoo14;"
```

2. Start Odoo:
```bash
cd /workspaces/odoo
python3 odoo-bin -c odoo.conf --http-port=8069
```

3. Open your browser to: `http://localhost:8069`

4. Use the database manager to create a new database and install modules.

### Method 2: Command Line Initialization

```bash
cd /workspaces/odoo

# Create and initialize database
PYTHONDONTWRITEBYTECODE=1 python3 odoo-bin -c odoo.conf -d odoo14 \
  --init=base,hr --without-demo=all --stop-after-init

# Start the server
python3 odoo-bin -c odoo.conf --http-port=8069
```

### Method 3: Using the startup script

```bash
cd /workspaces/odoo
./start-odoo.sh
```

Note: The `start-odoo.sh` script needs to be updated to use Docker PostgreSQL.

## Accessing Odoo

- URL: `http://localhost:8069`
- Master password: `admin`
- Database: `odoo14` (if created)
- Email: `admin`
- Password: (you'll set this during first login)

## Custom HR Theme Module

Your custom HR theme module is located at:
```
/workspaces/odoo/odoo-custom-addons/hr_custom_theme/
```

### Module Structure
```
hr_custom_theme/
├── __manifest__.py          # Module manifest
├── __init__.py              # Init file
├── static/
│   └── src/
│       └── css/
│           └── hr_custom_theme.css  # Custom styles
└── views/
    └── assets.xml           # Asset definitions
```

### Features
- Custom color scheme for HR module
- Styled employee forms, lists, and kanban cards
- Dashboard card styling
- Responsive design

### To Install the Custom Theme
1. Go to Apps menu in Odoo
2. Remove "Apps" filter
3. Search for "HR Custom Theme"
4. Click Install

## Managing the Docker PostgreSQL

### Start PostgreSQL
```bash
docker start odoo-postgres
```

### Stop PostgreSQL
```bash
docker stop odoo-postgres
```

### Restart PostgreSQL
```bash
docker restart odoo-postgres
```

### Check status
```bash
docker ps | grep postgres
```

## Troubleshooting

### Port 8069 already in use
```bash
pkill -f odoo-bin
```

### Recreate database
```bash
docker exec odoo-postgres psql -U odoo14 -d postgres -c "DROP DATABASE IF EXISTS odoo14;"
docker exec odoo-postgres psql -U odoo14 -d postgres -c "CREATE DATABASE odoo14;"
```

### Clear Python cache
```bash
find /workspaces/odoo -name "*.pyc" -delete
find /workspaces/odoo -name "__pycache__" -type d -exec rm -rf {} +
```

## GitHub Codespace Ports

To access Odoo from your browser in GitHub Codespace:
1. Click on "Ports" tab
2. Add port: `8069`
3. Set visibility to "Public" or "Private"

Then access via the provided URL.

## Next Steps

1. Start Odoo using one of the methods above
2. Create a new database via the web interface
3. Install the HR module
4. Install your custom HR theme module
5. Customize the theme in `/workspaces/odoo/odoo-custom-addons/hr_custom_theme/static/src/css/hr_custom_theme.css`
