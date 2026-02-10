# Odoo Setup Summary

## Done

- Python dependencies installed (from requirements.txt)
- `odoo.conf` created in project root. Update database credentials after installing PostgreSQL.
- `./data` directory created for Odoo

## Before first run

1. **Install PostgreSQL**  
   See `POSTGRESQL_SETUP.md` or `RUN_ODOO.md`. Create an `odoo` user or use `postgres`.

2. **Edit odoo.conf**  
   Set `db_user` and `db_password` (e.g. `odoo` / `odoo`).

3. **psycopg2 DLL error**  
   If you see: `ImportError: DLL load failed while importing _psycopg`  
   Install: https://aka.ms/vs/17/release/vc_redist.x64.exe

4. **Initialize database**  
   ```powershell
   python odoo-bin -c odoo.conf -d mycompany --stop-after-init -i base
   ```

5. **Start Odoo**  
   ```powershell
   python odoo-bin -c odoo.conf
   ```  
   Open http://localhost:8069

## Commands

```powershell
python odoo-bin --version
python odoo-bin -c odoo.conf -d mycompany --stop-after-init -i base
python odoo-bin -c odoo.conf
python odoo-bin -c odoo.conf -d mycompany
```

## Troubleshooting

**Cannot import psycopg2:** Install Visual C++ Redistributable (link above). Optionally: `pip install --force-reinstall psycopg2-binary`.

**Database errors:** PostgreSQL must be running. Check `db_host`, `db_port`, `db_user`, `db_password` in `odoo.conf`. Test: `psql -U postgres -h localhost`.

**Port in use:** Change `http_port` in `odoo.conf` (e.g. 8070) or stop the process on 8069.
