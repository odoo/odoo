# Manual Steps to Create Odoo Database User

## Quick Method (Copy & Paste)

Open PowerShell and run these commands one by one:

```powershell
# Navigate to PostgreSQL bin directory
cd "C:\Program Files\PostgreSQL\16\bin"

# Create the odoo user (will prompt for postgres password)
.\psql.exe -U postgres -c "CREATE USER odoo WITH PASSWORD 'odoo';"

# Grant database creation permission (will prompt for postgres password again)
.\psql.exe -U postgres -c "ALTER USER odoo CREATEDB;"

# Verify the user was created
.\psql.exe -U postgres -c "\du odoo"
```

**Note:** Each command will ask for the `postgres` user password. Enter the password you set during PostgreSQL installation.

---

## Alternative: Using pgAdmin (GUI Method)

1. Open **pgAdmin 4** from the Start menu
2. Enter the `postgres` password when prompted
3. In the left panel, expand **Servers** → **PostgreSQL 16**
4. Right-click on **Login/Group Roles** → **Create** → **Login/Group Role**
5. In the **General** tab:
   - Name: `odoo`
6. In the **Definition** tab:
   - Password: `odoo`
7. In the **Privileges** tab:
   - Check **Can login?**
   - Check **Create databases**
8. Click **Save**

---

## Verify User Creation

After creating the user, verify it works:

```powershell
cd "C:\Program Files\PostgreSQL\16\bin"
.\psql.exe -U odoo -d postgres -c "SELECT current_user;"
```

Enter password `odoo` when prompted. If it works, you'll see `current_user` = `odoo`.
