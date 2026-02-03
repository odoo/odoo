# Odoo Setup Completion Guide

## Current Status
- ✅ Odoo source code is present
- ✅ `setup.py` is configured
- ✅ `requirements.txt` exists with all dependencies
- ✅ Python dependencies installed (with compatible versions for Python 3.14)
- ✅ Odoo package installed
- ✅ Configuration file (`odoo.conf`) created
- ✅ Data directory created
- ❌ PostgreSQL database server not installed/configured
- ⚠️ Python version: 3.14.2 (Odoo officially supports 3.10-3.13, but works with 3.14)

## Steps to Complete Setup

### 1. Python Version (Recommended)
Odoo officially supports Python 3.10 through 3.13. You currently have Python 3.14.2, which may work but is outside the supported range. Consider:
- Installing Python 3.13 (recommended) or 3.12
- Using a virtual environment with the supported version

### 2. Install PostgreSQL Database Server
Odoo requires PostgreSQL 13 or higher.

**Windows Installation:**
- Download from: https://www.postgresql.org/download/windows/
- Install PostgreSQL 13+ with default settings
- Note the postgres user password you set during installation
- Ensure PostgreSQL service is running
- See `POSTGRESQL_SETUP.md` for detailed instructions

**Verify installation:**
```powershell
psql --version
```

**Note:** After installing PostgreSQL, update `odoo.conf` with your database credentials.

### 3. ✅ Python Dependencies (COMPLETED)
Install all required packages from `requirements.txt`:

```powershell
# Option 1: Using pip directly
pip install -r requirements.txt

# Option 2: Using setup.py (installs Odoo as a package)
pip install -e .

# Option 3: Install in a virtual environment (recommended)
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Note:** Some packages may require compilation on Windows. You may need:
- Microsoft Visual C++ Build Tools
- Or use pre-compiled wheels from: https://www.lfd.uci.edu/~gohlke/pythonlibs/

### 4. ✅ Configuration File (COMPLETED)
The `odoo.conf` file has been created in the project root.

**Important:** After installing PostgreSQL, update these settings in `odoo.conf`:
- `db_user`: Your PostgreSQL username
- `db_password`: Your PostgreSQL password

### 5. Initialize the Database
Create and initialize your first Odoo database:

```powershell
python odoo-bin -c odoo.conf -d your_database_name --stop-after-init -i base
```

This will:
- Create a new PostgreSQL database
- Install the base Odoo module
- Set up the initial database structure

### 6. Start Odoo Server
Run Odoo:

```powershell
python odoo-bin -c odoo.conf
```

Or with a specific database:

```powershell
python odoo-bin -c odoo.conf -d your_database_name
```

Access Odoo at: `http://localhost:8069`

### 7. First Login
- Default username: `admin`
- Default password: `admin` (change immediately!)

## Configuration File Template

See `odoo.conf.example` for a complete configuration template.

## Troubleshooting

### Common Issues:

1. **PostgreSQL Connection Error**
   - Verify PostgreSQL service is running
   - Check `db_host`, `db_port`, `db_user`, and `db_password` in config
   - Ensure PostgreSQL user has permission to create databases

2. **Missing Dependencies**
   - Some packages (like `psycopg2`, `lxml`, `Pillow`) may need compilation
   - Use pre-compiled wheels or install Visual C++ Build Tools

3. **Port Already in Use**
   - Change `http_port` in `odoo.conf` (default is 8069)
   - Or stop the process using port 8069

4. **Python Version Issues**
   - Use Python 3.10-3.13 for best compatibility
   - Check `odoo/release.py` for exact version requirements

## Additional Resources

- Official Documentation: https://www.odoo.com/documentation/master/administration/install/install.html
- Developer Setup: https://www.odoo.com/documentation/master/developer/tutorials/setup_guide.html
