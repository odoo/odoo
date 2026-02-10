# PostgreSQL Setup for Odoo

## Install

1. Download: https://www.postgresql.org/download/windows/ (PostgreSQL 13 or newer).
2. Run installer. Use default directory, data directory, port 5432. Set and remember the `postgres` password.

## Create Odoo user

**pgAdmin:** Connect as postgres. Login/Group Roles → Create. Name: `odoo`, Password: `odoo`. Privileges: Can login, Create databases. Save.

**Command line:**

```powershell
cd "C:\Program Files\PostgreSQL\16\bin"
.\psql.exe -U postgres
```

Then: `CREATE USER odoo WITH PASSWORD 'odoo';` and `ALTER USER odoo CREATEDB;` then `\q`.

Or use the `postgres` user and set `db_user` / `db_password` in `odoo.conf` accordingly.

## Odoo config

In `odoo.conf`: set `db_user` and `db_password` (e.g. `odoo` / `odoo`).

## Verify

```powershell
Get-Service -Name "*postgresql*"
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -c "SELECT version();"
```

## Initialize Odoo and start

```powershell
python odoo-bin -c odoo.conf -d mycompany --stop-after-init -i base
python odoo-bin -c odoo.conf
```

Open http://localhost:8069. Login: `admin` / `admin`. Change after first login.

## Troubleshooting

**Service not running:** `Start-Service postgresql-x64-16` or start via Win+R → services.msc.

**Connection refused:** Check service, firewall (5432), and `db_host` / `db_port` in `odoo.conf`.

**Authentication failed:** Check `odoo.conf` and user privileges (e.g. CREATEDB).

**Cannot create database:** `ALTER USER odoo CREATEDB;` as postgres.

## Reference

- Install path: `C:\Program Files\PostgreSQL\<version>\`, bin: `...\bin\`
- Start: `Start-Service postgresql-x64-16`. Stop: `Stop-Service postgresql-x64-16`.
