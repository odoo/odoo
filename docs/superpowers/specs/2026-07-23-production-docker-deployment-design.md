# Production Docker Deployment — Design

**Date:** 2026-07-23
**Scope:** Dockerfile, docker-compose.yml, entrypoint, Odoo config, and env template to deploy this Odoo 19 fork (aidt-odoo) into production.

## Context

- This repo is a full fork of the Odoo 19 community source (core + addons modified in-tree), so the image is **built from this source**, not overlaid on the official `odoo:19` image.
- The host already runs a reverse proxy that terminates SSL. The stack therefore binds ports to `127.0.0.1` only and Odoo runs with `proxy_mode = True`.
- PostgreSQL runs as a container in the same compose file.
- Target server: ~4 CPU / 8 GB RAM → `workers = 5` (cores × 2 + 1), `max_cron_threads = 2`.

## Deliverables

| File | Purpose |
|------|---------|
| `Dockerfile` | Multi-stage image build from this source |
| `docker-compose.yml` | Production stack: `db` + `odoo` |
| `docker/entrypoint.sh` | Wait for Postgres, render config from env, exec odoo-bin |
| `docker/odoo.conf` | Production Odoo configuration template |
| `.env.example` | Documented environment variables (secrets never committed) |
| `.dockerignore` | Keep build context lean |

## Dockerfile (multi-stage, `python:3.12-slim`)

**Build stage:**
- Install build deps: `build-essential`, `libpq-dev`, `libldap2-dev`, `libsasl2-dev`, `libssl-dev`, etc.
- Create a venv at `/opt/venv`; `pip install -r requirements.txt` plus `psycopg2` (source build against libpq).

**Runtime stage:**
- Runtime libs only: `libpq5`, `libldap`, `libsasl2`, `libxml2`, `libxslt`, fonts (`fonts-noto-cjk`, `fonts-liberation`), `postgresql-client`.
- **wkhtmltopdf 0.12.6.1** (patched-qt build from the official wkhtmltopdf GitHub releases, bookworm `.deb`) — required for PDF report headers/footers.
- `nodejs` + `npm install -g rtlcss` for right-to-left language asset support.
- Non-root `odoo` user (uid 101); source copied to `/opt/odoo`; filestore dir `/var/lib/odoo` owned by `odoo`.
- `ENTRYPOINT ["/entrypoint.sh"]`, default `CMD` runs `odoo-bin -c /etc/odoo/odoo.conf`.
- `EXPOSE 8069 8072`.

## Odoo configuration (`docker/odoo.conf`)

Values chosen for 4 CPU / 8 GB:

```
workers = 5
max_cron_threads = 2
limit_memory_soft = 1073741824      ; 1 GiB per worker
limit_memory_hard = 1342177280      ; 1.25 GiB per worker
limit_time_cpu = 600
limit_time_real = 1200
proxy_mode = True
list_db = False
admin_passwd = <from env>
db_host/db_port/db_user/db_password = <from env>
data_dir = /var/lib/odoo
gevent_port = 8072
```

Secrets (`admin_passwd`, `db_password`) are injected by the entrypoint from environment variables — the committed config file contains no secrets. Worker count also overridable via env (`ODOO_WORKERS`) without rebuilding.

## docker-compose.yml

- `db`: `postgres:16-alpine`, `POSTGRES_USER=odoo`, password from `.env`, named volume `db-data`, healthcheck (`pg_isready`), `restart: unless-stopped`.
- `odoo`: `build: .`, `depends_on: db: condition: service_healthy`, named volume `odoo-filestore` → `/var/lib/odoo`, ports `127.0.0.1:8069:8069` and `127.0.0.1:8072:8072`, env from `.env`, `restart: unless-stopped`, logs to stdout (json-file with rotation limits).
- Named volumes: `db-data`, `odoo-filestore`.

**Reverse-proxy contract:** the existing proxy must forward HTTP to `:8069` and route `/websocket` to `:8072`, passing `X-Forwarded-*` headers (honoured because `proxy_mode = True`).

## Error handling

- Entrypoint retries Postgres connection (bounded, ~30 attempts) before starting Odoo; exits non-zero on failure so `restart: unless-stopped` retries.
- Container healthcheck on `/web/health`.

## Testing

- `docker compose build` completes.
- `docker compose up` → healthcheck passes, `/web/database/selector` blocked (`list_db = False`), `/web/health` returns 200.
- PDF generation and websocket routing verified after proxy wiring (manual, on the target host).

## Out of scope

- Reverse proxy configuration (exists already), backups, CI/CD image publishing, Odoo Enterprise addons.
