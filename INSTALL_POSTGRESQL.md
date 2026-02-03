# Step-by-Step PostgreSQL Installation for Odoo

## Step 1: Download PostgreSQL

1. Open your web browser
2. Go to: **https://www.postgresql.org/download/windows/**
3. Click on **"Download the installer"** (it will redirect to EnterpriseDB)
4. Download the **Windows x86-64** installer for the latest version (PostgreSQL 16 or 15 recommended)

## Step 2: Install PostgreSQL

1. **Run the installer** you just downloaded
2. Click **"Next"** on the welcome screen
3. **Installation Directory**: Keep the default (`C:\Program Files\PostgreSQL\16`) and click **Next**
4. **Select Components**: Keep all checked (PostgreSQL Server, pgAdmin 4, Stack Builder, Command Line Tools) and click **Next**
5. **Data Directory**: Keep the default and click **Next**
6. **Password**: 
   - Enter a password for the `postgres` superuser
   - **IMPORTANT**: Remember this password! You'll need it.
   - Click **Next**
7. **Port**: Keep default **5432** and click **Next**
8. **Advanced Options**: Keep default locale and click **Next**
9. **Pre Installation Summary**: Click **Next**
10. **Ready to Install**: Click **Next**
11. Wait for installation to complete
12. **Completing the PostgreSQL Setup**: 
    - Uncheck "Launch Stack Builder" (we don't need it)
    - Click **Finish**

## Step 3: Verify Installation

Open PowerShell and run:

```powershell
# Check if PostgreSQL service is running
Get-Service -Name "*postgresql*"
```

You should see a service like `postgresql-x64-16` with status "Running"

## Step 4: Create Odoo Database User (Recommended)

### Option A: Using pgAdmin (GUI - Easier)

1. Open **pgAdmin 4** from the Start menu
2. When it opens, you'll be prompted for the `postgres` user password (the one you set during installation)
3. In the left panel, expand **Servers** → **PostgreSQL 16** (or your version)
4. Right-click on **Login/Group Roles** → **Create** → **Login/Group Role**
5. In the **General** tab:
   - Name: `odoo`
6. In the **Definition** tab:
   - Password: `odoo` (or your preferred password)
7. In the **Privileges** tab:
   - Check **Can login?**
   - Check **Create databases**
8. Click **Save**

### Option B: Using Command Line

1. Open PowerShell
2. Navigate to PostgreSQL bin directory (adjust version number if needed):
   ```powershell
   cd "C:\Program Files\PostgreSQL\16\bin"
   ```
3. Connect to PostgreSQL:
   ```powershell
   .\psql.exe -U postgres
   ```
4. Enter the `postgres` password when prompted
5. Run these SQL commands:
   ```sql
   CREATE USER odoo WITH PASSWORD 'odoo';
   ALTER USER odoo CREATEDB;
   \q
   ```

## Step 5: Update Odoo Configuration

1. Open `odoo.conf` in your project directory
2. Update these lines with your PostgreSQL settings:

```ini
db_user = odoo
db_password = odoo
```

Or if you want to use the `postgres` user instead:
```ini
db_user = postgres
db_password = <your_postgres_password>
```

## Step 6: Test Database Connection

In PowerShell, test the connection:

```powershell
# Navigate to PostgreSQL bin (adjust version)
cd "C:\Program Files\PostgreSQL\16\bin"

# Test connection with odoo user
.\psql.exe -U odoo -d postgres -c "SELECT version();"
```

Enter password when prompted. If it works, you'll see PostgreSQL version info.

## Step 7: Initialize Odoo Database

Now you can create your first Odoo database:

```powershell
# Make sure you're in the odoo project directory
cd C:\Neumont\2ndYear\3rdQuarter\ServiceBasedSoftwareArch\odoo

# Initialize database
python odoo-bin -c odoo.conf -d mycompany --stop-after-init -i base
```

This will:
- Create a database named `mycompany`
- Install the base Odoo module
- Set up the initial structure

## Step 8: Start Odoo Server

```powershell
python odoo-bin -c odoo.conf
```

Or start with a specific database:
```powershell
python odoo-bin -c odoo.conf -d mycompany
```

## Step 9: Access Odoo

1. Open your web browser
2. Go to: **http://localhost:8069**
3. You should see the Odoo database manager or login screen
4. Default login (if database already initialized):
   - Username: `admin`
   - Password: `admin` (change immediately!)

## Troubleshooting

### PostgreSQL Service Not Running

```powershell
# Start the service
Start-Service postgresql-x64-16

# Or use Services GUI
# Press Win+R, type: services.msc
# Find PostgreSQL service and start it
```

### Can't Connect to Database

1. Verify PostgreSQL service is running
2. Check firewall isn't blocking port 5432
3. Verify username and password in `odoo.conf`
4. Test connection manually:
   ```powershell
   cd "C:\Program Files\PostgreSQL\16\bin"
   .\psql.exe -U odoo -d postgres
   ```

### psycopg2 DLL Error

If you see: `ImportError: DLL load failed while importing _psycopg`

1. Download Visual C++ Redistributable: https://aka.ms/vs/17/release/vc_redist.x64.exe
2. Install it
3. Restart your terminal/PowerShell
4. Try running Odoo again

### Permission Denied

If you get permission errors:
```sql
-- Connect as postgres user
-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE mycompany TO odoo;
```

## Quick Reference

**PostgreSQL Default Locations:**
- Installation: `C:\Program Files\PostgreSQL\16\`
- Data: `C:\Program Files\PostgreSQL\16\data`
- Bin: `C:\Program Files\PostgreSQL\16\bin\`

**Common Commands:**
```powershell
# Start PostgreSQL service
Start-Service postgresql-x64-16

# Stop PostgreSQL service
Stop-Service postgresql-x64-16

# Connect to PostgreSQL
cd "C:\Program Files\PostgreSQL\16\bin"
.\psql.exe -U postgres

# List databases (in psql)
\l

# Create database (in psql)
CREATE DATABASE testdb;
```
