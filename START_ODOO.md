# Starting Odoo

## Prerequisites

- PostgreSQL installed and running
- Odoo database user created (e.g. `odoo` / `odoo`)
- `odoo.conf` updated with correct `db_user` and `db_password`

## Initialize database (first time only)

Creates the database and installs the base module:

```powershell
cd C:\Neumont\2ndYear\3rdQuarter\ServiceBasedSoftwareArch\odoo
python odoo-bin -c odoo.conf -d mycompany --stop-after-init -i base
```

Replace `mycompany` with your database name. This may take 5–10 minutes.

## Start Odoo

```powershell
cd C:\Neumont\2ndYear\3rdQuarter\ServiceBasedSoftwareArch\odoo
python odoo-bin -c odoo.conf
```

With a specific database:

```powershell
python odoo-bin -c odoo.conf -d mycompany
```

## Access

Open: http://localhost:8069

- First time: create or select a database. Master password is in `odoo.conf` (`admin_passwd`).
- Login: default is `admin` / `admin`. Change this after first login.

## Config summary

In `odoo.conf`:

- Database: PostgreSQL on localhost:5432
- User/password: set in `db_user` and `db_password`
- Web: http://localhost:8069
- Data directory: `./data`

## Troubleshooting

**Port 8069 in use**  
Change `http_port` in `odoo.conf` (e.g. to 8070) or stop the process using 8069.

**Database connection error**  
- Check PostgreSQL is running: `Get-Service postgresql-x64-16`
- Check `odoo.conf` credentials
- Test: `psql -U odoo -d postgres`

**Page does not load**  
- Ensure the Odoo process is running
- Check `odoo.log` for errors
- Try http://127.0.0.1:8069
