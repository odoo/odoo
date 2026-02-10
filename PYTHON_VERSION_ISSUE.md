# Python 3.14 Compatibility Issue

## The Problem

You're experiencing errors because:
1. **Python 3.14 is not officially supported** by Odoo 19
2. Odoo 19 officially supports Python 3.10 through 3.13
3. There are template rendering errors with Python 3.14's security restrictions

## Error You're Seeing

```
ValueError: forbidden opcode(s) in 'insecure and databases': NOT_TAKEN
```

This is a Python 3.14 security feature that blocks certain operations that Odoo's template engine uses.

## Solutions

### Option 1: Use Python 3.13 (Recommended)

1. **Install Python 3.13:**
   - Download from: https://www.python.org/downloads/
   - Install Python 3.13.x (latest 3.13 version)

2. **Create a virtual environment with Python 3.13:**
   ```powershell
   # Find where Python 3.13 is installed (usually C:\Python313 or C:\Users\YourName\AppData\Local\Programs\Python\Python313)
   # Then create venv:
   C:\Python313\python.exe -m venv venv313
   .\venv313\Scripts\Activate.ps1
   ```

3. **Reinstall dependencies:**
   ```powershell
   pip install -r requirements.txt
   pip install psycopg2-binary
   pip install -e .
   ```

4. **Run Odoo with Python 3.13:**
   ```powershell
   .\venv313\Scripts\python.exe odoo-bin -c odoo.conf
   ```

### Option 2: Work Around Python 3.14 Issues (Temporary)

The database has been created. You can try:

1. **Start Odoo with a specific database** (bypasses the database manager):
   ```powershell
   python odoo-bin -c odoo.conf -d NinetyDays
   ```

2. **If database needs initialization:**
   ```powershell
   python odoo-bin -c odoo.conf -d NinetyDays --stop-after-init -i base
   ```

3. **Then access directly:**
   - Go to: http://localhost:8069
   - You should see login screen (not database manager)

### Option 3: Use Docker (Alternative)

If Python version management is difficult, consider using Odoo via Docker, which comes with the correct Python version pre-configured.

## Current Status

- Database "NinetyDays" has been created.
- PostgreSQL is working.
- Web interface may have Python 3.14 compatibility issues.
- You can bypass the database manager by starting with `-d NinetyDays`.

## Recommended Action

**Install Python 3.13** for the best compatibility with Odoo 19. This will resolve all the template rendering errors and allow the database manager to work properly.
