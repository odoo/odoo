# Quick Start

## Start Odoo

From the project folder:

```powershell
python odoo-bin -c odoo.conf
```

Open: http://localhost:8069

Default login: `admin` / `admin`. Change after first login.

## First time

If you see the database manager:

- Create a database (e.g. name: `mycompany`, master password from `odoo.conf`)
- Or select an existing database

If you see the login screen, use `admin` / `admin`.

## Stop Odoo

In the terminal: Ctrl+C.

Or in Task Manager, end the Python process running Odoo.

## Start again later

```powershell
cd C:\Neumont\2ndYear\3rdQuarter\ServiceBasedSoftwareArch\odoo
python odoo-bin -c odoo.conf -d mycompany
```

## Troubleshooting

**Page does not load**  
Wait a bit on first start. Check Python is running and `odoo.log` for errors.

**Database error**  
PostgreSQL must be running: `Get-Service postgresql-x64-16`. Check `odoo.conf` database settings.

**Port in use**  
Change `http_port` in `odoo.conf` (e.g. 8070) or stop the process on 8069.
