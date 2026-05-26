#!/bin/bash
set -e

# Write /etc/odoo/odoo.conf from environment variables at container start.
cat > /etc/odoo/odoo.conf <<EOF
[options]
addons_path = /opt/odoo/server/addons

admin_passwd = ${ODOO_MASTER_PASSWORD:-rkpassword}

db_host     = ${DB_HOST:-postgres}
db_port     = ${DB_PORT:-5432}
db_user     = ${DB_USER:-odoo}
db_password = ${DB_PASSWORD:-odoo}
db_name     = ${DB_NAME:-odoo-db}
db_template = template0
db_maxconn  = 64
db_sslmode  = prefer

list_db    = False
proxy_mode = True
dbfilter   = ^${DB_NAME:-odoo-db}$

http_interface = 0.0.0.0
http_port      = 8069
gevent_port    = 8072

workers          = ${ODOO_WORKERS:-9}
max_cron_threads = 2

limit_memory_soft = 671088640
limit_memory_hard = 805306368
limit_request     = 65536
limit_time_cpu           = 60
limit_time_real          = 120
limit_time_real_cron     = -1

log_level   = warn
log_handler = :WARNING
logfile     = /var/log/odoo/odoo.log

data_dir = /var/lib/odoo

server_wide_modules = base,web
with_demo           = False
EOF

# Auto-initialize database on first run (skipped if Odoo tables already exist)
if ! python3 -c "
import os, psycopg2
conn = psycopg2.connect(
    host=os.getenv('DB_HOST','postgres'),
    port=os.getenv('DB_PORT','5432'),
    user=os.getenv('DB_USER','odoo'),
    password=os.getenv('DB_PASSWORD','odoo'),
    dbname=os.getenv('DB_NAME','odoo-db'),
    connect_timeout=10
)
cur = conn.cursor()
cur.execute(\"SELECT to_regclass('public.res_users')\")
assert cur.fetchone()[0] is not None
conn.close()" 2>/dev/null; then
    echo "[entrypoint] Fresh database detected — running first-time initialization..."
    /opt/odoo/server/odoo-bin \
        -c /etc/odoo/odoo.conf \
        -i base \
        --stop-after-init \
        --workers=0
    echo "[entrypoint] Initialization complete."
fi

exec "$@"
