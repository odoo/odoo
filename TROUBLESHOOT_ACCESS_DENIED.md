# Troubleshooting "Access Denied" Error

## Current Configuration

Your `odoo.conf` currently has:
```ini
admin_passwd = odoo123
```

**Try using `odoo123` as the Master Password in the web interface.**

## Step-by-Step Troubleshooting

### Step 1: Verify You're Using the Correct Password

The Master Password in the web interface **MUST match** the `admin_passwd` in `odoo.conf`.

**Current setting:** `admin_passwd = odoo123`

**So use:** `odoo123` as the Master Password

### Step 2: Check for Common Issues

1. **Case Sensitivity:** Passwords are case-sensitive
   - Use exactly: `odoo123` (all lowercase)

2. **No Extra Spaces:** Make sure there are no spaces before or after the password

3. **Browser Cache:** Try:
   - Hard refresh: `Ctrl + F5`
   - Or clear browser cache
   - Or try in an incognito/private window

### Step 3: Verify Database User Permissions

The database user should have SUPERUSER privileges (already granted):
```sql
-- Verify with:
psql -U postgres -c "\du odoo"
-- Should show: Superuser, Create DB
```

### Step 4: Check Odoo Logs

Check for specific error messages:
```powershell
Get-Content odoo.log -Tail 30
```

Look for:
- "Access denied" messages
- Database connection errors
- Permission errors

### Step 5: Try Creating Database via Command Line

As a test, try creating a database manually:
```powershell
$env:PGPASSWORD = "odoo"
cd "C:\Program Files\PostgreSQL\16\bin"
.\psql.exe -U odoo -d postgres -c "CREATE DATABASE testdb;"
```

If this works, the issue is with Odoo's password validation, not database permissions.

### Step 6: Alternative - Change Master Password Back

If `odoo123` doesn't work, let's try a simpler password:

1. Edit `odoo.conf`:
   ```ini
   admin_passwd = test123
   ```

2. Restart Odoo server

3. Use `test123` as Master Password

### Step 7: Check if Database Already Exists

If you're trying to create a database named "NinetyDays" and it already exists, you'll get an error. Check:
```powershell
$env:PGPASSWORD = "odoo"
cd "C:\Program Files\PostgreSQL\16\bin"
.\psql.exe -U odoo -d postgres -c "\l" | Select-String "NinetyDays"
```

If it exists, either:
- Use a different database name
- Or delete it first: `DROP DATABASE "NinetyDays";`

## Still Not Working?

If none of the above works, the issue might be:

1. **Odoo version compatibility issue** - Python 3.14 is not officially supported
2. **Config file not being read** - Try specifying config explicitly
3. **Web interface bug** - Try using Odoo's command-line database creation

### Command-Line Database Creation (Alternative)

Instead of using the web interface, create the database via command line:

```powershell
cd C:\Neumont\2ndYear\3rdQuarter\ServiceBasedSoftwareArch\odoo
python odoo-bin -c odoo.conf -d NinetyDays --stop-after-init -i base
```

This will:
- Create the database "NinetyDays"
- Install the base module
- Initialize all tables

Then start Odoo normally and you can log in.
