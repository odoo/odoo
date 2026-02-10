# Running PostgreSQL and Odoo

## 1. PostgreSQL

**Install (one-time)**  
- Download: https://www.postgresql.org/download/windows/  
- Run the installer. Use default port 5432. Set and remember the `postgres` password.

**Create Odoo user (one-time)**  
In PowerShell:

```powershell
cd "C:\Program Files\PostgreSQL\16\bin"
.\psql.exe -U postgres
```

At the prompt:

```sql
CREATE USER odoo WITH PASSWORD 'odoo';
ALTER USER odoo CREATEDB;
\q
```

**Start PostgreSQL**  
PostgreSQL usually runs as a Windows service. To start it:

```powershell
Start-Service postgresql-x64-16
```

(Use your version number if different. Check: `Get-Service -Name "*postgresql*"`.)

**Check it is running**  
```powershell
.\psql.exe -U odoo -d postgres -c "SELECT 1;"
```

If that works, PostgreSQL is ready.

---

## 2. Odoo

**Config**  
In the project folder, open `odoo.conf` and set:

- `db_user = odoo`
- `db_password = odoo`

(Or use `postgres` and its password if you did not create `odoo`.)

**First-time: create database**  
From the project folder (e.g. `C:\Neumont\2ndYear\3rdQuarter\ServiceBasedSoftwareArch\odoo`):

```powershell
python odoo-bin -c odoo.conf -d NinetyDays --stop-after-init -i base
```

Use your database name instead of `NinetyDays` if different. This can take several minutes.

**Start Odoo**  
```powershell
python odoo-bin -c odoo.conf
```

Or with a specific database:

```powershell
python odoo-bin -c odoo.conf -d NinetyDays
```

**Open in browser**  
http://localhost:8069  

Default login: `admin` / `admin`. Change the password after first login.

**Stop Odoo**  
In the terminal where it is running: press Ctrl+C.  
Or in Task Manager, end the Python process that is running Odoo.

---

## Troubleshooting

**PostgreSQL not running**  
- Start service: `Start-Service postgresql-x64-16`  
- Or: Win+R, type `services.msc`, find PostgreSQL, start it.

**Odoo cannot connect to database**  
- Confirm PostgreSQL is running.  
- Check `db_host`, `db_port`, `db_user`, `db_password` in `odoo.conf`.  
- Test: `.\psql.exe -U odoo -d postgres -c "SELECT 1;"` from PostgreSQL bin.

**Port 8069 in use**  
- Change `http_port` in `odoo.conf` (e.g. to 8070), or stop the program using 8069.

**psycopg2 DLL error**  
- Install Visual C++ Redistributable: https://aka.ms/vs/17/release/vc_redist.x64.exe  
- Then run Odoo again.
