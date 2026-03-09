# Dev Project Mode

This mode is for working on the actual `kodoo` project with a light stack:

- Odoo runs on the host via Python
- PostgreSQL runs in Docker
- `ktest` is the default database
- `ollama`, `nginx`, and `cloudflared` stay down

## Use

```bash
make dev-project-up
```

That will:

1. start Docker PostgreSQL on `127.0.0.1:5433`
2. ensure `ktest` exists
3. generate `deploy/odoo/kodoo.dev-project.local.conf`
4. start Odoo on the host at `http://127.0.0.1:8069`

## Main targets

```bash
make dev-project-db-init
make dev-project-up
make dev-project-status
make dev-project-logs
make dev-project-stop
```

Mode aliases:

```bash
make up-project
make smoke-project
make troubleshoot-project
make down-project
```

## Environment

Relevant `.env.make` values:

```bash
DOCKER_DB_BIND_HOST=127.0.0.1
DOCKER_DB_HOST_PORT=5433
DEV_PROJECT_DB=ktest
DEV_PROJECT_ADMIN_PASSWORD=
PROD_DB_USER=kodoo
PROD_DB_PASSWORD=...
```

If `DEV_PROJECT_ADMIN_PASSWORD` is empty, the mode falls back to `DEV_HOST_ADMIN_PASSWORD`, and then to `PROD_ADMIN_PASSWORD`.
