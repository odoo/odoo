# PostgreSQL Setup for Odoo

## Installation Steps

### 1. Download PostgreSQL
- Visit: https://www.postgresql.org/download/windows/
- Download the Windows installer (recommended: PostgreSQL 13 or newer)
- Run the installer

### 2. Installation Configuration
During installation, you'll be prompted to:
- **Installation Directory**: Use default (usually `C:\Program Files\PostgreSQL\<version>`)
- **Data Directory**: Use default
- **Password**: Set a password for the `postgres` superuser (remember this!)
- **Port**: Use default (5432)
- **Locale**: Use default

### 3. Post-Installation Setup

#### Option A: Create a dedicated Odoo database user (Recommended)
After installation, open **pgAdmin** (included with PostgreSQL) or use **psql** command line:

```sql
-- Connect as postgres user, then run:
CREATE USER odoo WITH PASSWORD 'odoo';
ALTER USER odoo CREATEDB;
```

Or using psql command line:
```powershell
# Find PostgreSQL bin directory (usually C:\Program Files\PostgreSQL\<version>\bin)
cd "C:\Program Files\PostgreSQL\16\bin"
.\psql.exe -U postgres

# Then in psql prompt:
CREATE USER odoo WITH PASSWORD 'odoo';
ALTER USER odoo CREATEDB;
\q
```

#### Option B: Use the postgres user
You can use the `postgres` user directly. Update `odoo.conf`:
```
db_user = postgres
db_password = <your_postgres_password>
```

### 4. Update Odoo Configuration
Edit `odoo.conf` and update:
- `db_user`: Your PostgreSQL username (e.g., `odoo` or `postgres`)
- `db_password`: Your PostgreSQL password

### 5. Verify PostgreSQL is Running
```powershell
# Check if PostgreSQL service is running
Get-Service -Name "*postgresql*"

# Or test connection
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -c "SELECT version();"
```

### 6. Initialize Your First Odoo Database
Once PostgreSQL is configured, initialize your database:

```powershell
python odoo-bin -c odoo.conf -d mycompany --stop-after-init -i base
```

This will:
- Create a database named `mycompany`
- Install the base Odoo module
- Set up the initial database structure

### 7. Start Odoo Server
```powershell
python odoo-bin -c odoo.conf
```

Or with a specific database:
```powershell
python odoo-bin -c odoo.conf -d mycompany
```

Access Odoo at: **http://localhost:8069**

## Troubleshooting

### PostgreSQL Service Not Running
```powershell
# Start PostgreSQL service
Start-Service postgresql-x64-16  # Adjust version number as needed

# Or use Services GUI: Win+R -> services.msc -> Find PostgreSQL service -> Start
```

### Connection Refused
- Verify PostgreSQL service is running
- Check firewall settings (port 5432)
- Verify `db_host`, `db_port` in `odoo.conf`

### Authentication Failed
- Verify username and password in `odoo.conf`
- Check PostgreSQL `pg_hba.conf` file (usually in data directory)
- Ensure user has `CREATEDB` privilege

### Cannot Create Database
- Ensure the database user has `CREATEDB` privilege:
  ```sql
  ALTER USER odoo CREATEDB;
  ```

## Quick Reference

**PostgreSQL Default Locations:**
- Installation: `C:\Program Files\PostgreSQL\<version>\`
- Data: `C:\Program Files\PostgreSQL\<version>\data`
- Bin: `C:\Program Files\PostgreSQL\<version>\bin\`

**Common Commands:**
```powershell
# Connect to PostgreSQL
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres

# List databases
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -c "\l"

# Create database
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -c "CREATE DATABASE testdb;"
```
