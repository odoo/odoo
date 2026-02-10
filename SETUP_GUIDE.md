# Odoo Setup Guide

## Status

- Odoo source, setup.py, requirements.txt present
- Dependencies installed; odoo.conf and data directory created
- PostgreSQL must be installed and configured separately (see POSTGRESQL_SETUP.md or RUN_ODOO.md)

Python: Odoo supports 3.10–3.13. Python 3.14 may work but is unsupported. Prefer 3.13 or 3.12.

## Steps

### 1. Install PostgreSQL

- Download: https://www.postgresql.org/download/windows/
- Install PostgreSQL 13+ with defaults. Remember the postgres password.
- Ensure the PostgreSQL service is running. Create an `odoo` user (see POSTGRESQL_SETUP.md).

### 2. Python dependencies

Already done if you ran:

```powershell
pip install -r requirements.txt
# or
pip install -e .
```

For a clean environment: `python -m venv venv`, activate, then `pip install -r requirements.txt`.

### 3. Configuration

Update `odoo.conf` with database credentials:

- `db_user`: PostgreSQL username (e.g. odoo or postgres)
- `db_password`: PostgreSQL password

### 4. Initialize database

```powershell
python odoo-bin -c odoo.conf -d your_database_name --stop-after-init -i base
```

Creates the database and installs the base module.

### 5. Start Odoo

```powershell
python odoo-bin -c odoo.conf
# or with a database name:
python odoo-bin -c odoo.conf -d your_database_name
```

Open http://localhost:8069. Login: `admin` / `admin`. Change after first login.

## Troubleshooting

**PostgreSQL connection:** Check service is running and db_host, db_port, db_user, db_password in odoo.conf. User needs permission to create databases.

**Missing dependencies:** Some packages may need Visual C++ Build Tools or pre-built wheels on Windows.

**Port in use:** Change `http_port` in odoo.conf (default 8069) or stop the process using it.

**Python version:** Use 3.10–3.13 for best compatibility.
