# PostgreSQL Installation for Odoo

## Download

1. Go to https://www.postgresql.org/download/windows/
2. Download the Windows x86-64 installer (PostgreSQL 16 or 15).

## Install

1. Run the installer. Click Next on the welcome screen.
2. Installation directory: keep default. Next.
3. Components: keep all (PostgreSQL Server, pgAdmin 4, Stack Builder, Command Line Tools). Next.
4. Data directory: default. Next.
5. Password: set a password for the `postgres` user. Remember it. Next.
6. Port: 5432. Next.
7. Locale: default. Next.
8. Finish the wizard. Uncheck "Launch Stack Builder" at the end. Finish.

## Verify

```powershell
Get-Service -Name "*postgresql*"
```

Status should be Running (e.g. `postgresql-x64-16`).

## Create Odoo user

**pgAdmin:**  
Servers → PostgreSQL 16 → Login/Group Roles → Create → Login/Group Role. Name: `odoo`. Password: `odoo`. Privileges: Can login, Create databases. Save.

**Command line:**

```powershell
cd "C:\Program Files\PostgreSQL\16\bin"
.\psql.exe -U postgres
```

Enter postgres password, then:

```sql
CREATE USER odoo WITH PASSWORD 'odoo';
ALTER USER odoo CREATEDB;
\q
```

## Update odoo.conf

Set:

```ini
db_user = odoo
db_password = odoo
```

Or use `postgres` and its password.

## Test connection

```powershell
cd "C:\Program Files\PostgreSQL\16\bin"
.\psql.exe -U odoo -d postgres -c "SELECT version();"
```

## Initialize Odoo and start

```powershell
cd C:\Neumont\2ndYear\3rdQuarter\ServiceBasedSoftwareArch\odoo
python odoo-bin -c odoo.conf -d mycompany --stop-after-init -i base
python odoo-bin -c odoo.conf
```

Open http://localhost:8069. Login: `admin` / `admin`. Change password after first login.

## Troubleshooting

**Service not running**  
`Start-Service postgresql-x64-16` or start via services.msc.

**Cannot connect**  
Check service, firewall (5432), and `odoo.conf`. Test with psql as above.

**psycopg2 DLL error**  
Install: https://aka.ms/vs/17/release/vc_redist.x64.exe

**Permission denied**  
As postgres: `GRANT ALL PRIVILEGES ON DATABASE mycompany TO odoo;`
