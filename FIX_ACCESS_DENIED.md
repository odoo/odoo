# Fix "Access Denied" Error in Odoo Database Manager

## The Problem

When you try to create or restore a database in Odoo, you get "Access Denied" error.

## The Solution

### Step 1: Use the Correct Master Password

Your `odoo.conf` file has this setting:
```ini
admin_passwd = admin
```

**When creating/restoring a database, you MUST use `admin` as the Master Password.**

### Step 2: Create Database Steps

1. Open http://localhost:8069 in your browser
2. You'll see the **Database Manager** screen
3. Fill in the form:
   - **Database Name:** `mycompany` (or any name you want)
   - **Master Password:** `admin` (must match admin_passwd in odoo.conf)
   - **Language:** Select your language
   - **Country:** Select your country
   - **Demo data:** Check if you want sample data
4. Click **"Create Database"**

### Step 3: If Still Getting Access Denied

#### Option A: Restart Odoo Server

1. Stop the current Odoo server:
   ```powershell
   Get-Process python | Where-Object {$_.CommandLine -like '*odoo*'} | Stop-Process
   ```

2. Start it again:
   ```powershell
   cd C:\Neumont\2ndYear\3rdQuarter\ServiceBasedSoftwareArch\odoo
   python odoo-bin -c odoo.conf
   ```

#### Option B: Change the Master Password

If you want to use a different master password:

1. Edit `odoo.conf`:
   ```ini
   admin_passwd = your_new_password
   ```

2. Restart Odoo server

3. Use `your_new_password` in the Database Manager

#### Option C: Verify Configuration

Make sure your `odoo.conf` has:
```ini
admin_passwd = admin
db_user = odoo
db_password = odoo
```

## Understanding Master Password

The **Master Password** (`admin_passwd`) is different from:
- Your Odoo login password (admin/admin)
- Your PostgreSQL password

It's a special password that Odoo uses to:
- Create new databases
- Restore databases
- Delete databases
- Manage database operations

## Verification

- Database user `odoo` should have CREATEDB permission.
- `odoo.conf` should have `admin_passwd = admin`.
- PostgreSQL should be running.

Use `admin` as the Master Password in the Database Manager.

## Still Having Issues?

If you're still getting access denied after using `admin` as the master password:

1. Check the Odoo log file:
   ```powershell
   Get-Content odoo.log -Tail 20
   ```

2. Verify PostgreSQL connection:
   ```powershell
   cd "C:\Program Files\PostgreSQL\16\bin"
   .\psql.exe -U odoo -d postgres
   ```

3. Try creating database manually to test:
   ```powershell
   $env:PGPASSWORD = "odoo"
   cd "C:\Program Files\PostgreSQL\16\bin"
   .\psql.exe -U odoo -d postgres -c "CREATE DATABASE testdb;"
   ```
