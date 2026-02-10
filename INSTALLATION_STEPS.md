# PostgreSQL Installation Steps

## Download

1. Go to https://www.enterprisedb.com/downloads/postgres-postgresql-downloads (or https://www.postgresql.org/download/windows/).
2. Choose PostgreSQL 16 (or 15), Windows x86-64.
3. Download the installer (e.g. postgresql-16.11-1-windows-x64.exe). It is usually in your Downloads folder.

## Install

1. Run the installer. Click Next on the welcome screen.
2. Installation directory: keep default (e.g. C:\Program Files\PostgreSQL\16). Next.
3. Components: keep PostgreSQL Server, pgAdmin 4, Command Line Tools. Next.
4. Data directory: default. Next.
5. Password: set a password for the `postgres` user. Remember it. Next.
6. Port: 5432. Next.
7. Locale: default. Next.
8. Complete the wizard. At the end, uncheck "Launch Stack Builder". Finish.

## After install

1. Verify the service: `Get-Service -Name "*postgresql*"` (should be Running).
2. Create the Odoo user (see POSTGRESQL_SETUP.md or RUN_ODOO.md).
3. Update odoo.conf with db_user and db_password.
4. Test: from PostgreSQL bin, run `.\psql.exe -U odoo -d postgres -c "SELECT version();"`
