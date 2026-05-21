# Deploying Odoo on Railway

This directory contains the assets used by the top-level `Dockerfile` to build
an Odoo image that runs on [Railway](https://railway.com).

## Files

| Path                     | Purpose                                                          |
| ------------------------ | ---------------------------------------------------------------- |
| `../Dockerfile`          | Image definition (Ubuntu 24.04 + Odoo 19.0 + wkhtmltopdf 0.12.6) |
| `../railway.json`        | Railway build/deploy config (Dockerfile builder, healthcheck)    |
| `../.dockerignore`       | Keeps build context lean                                         |
| `entrypoint.sh`          | Translates Railway env vars into Odoo CLI flags                  |
| `odoo.conf`              | Baseline Odoo config (proxy_mode, no DB manager, etc.)           |

## One-time setup on Railway

1. Create a new project and add a **PostgreSQL** plugin. Railway will set
   `DATABASE_URL` on the Odoo service automatically once the plugin is linked.
2. Add this repository as a service. Railway detects `railway.json` and uses
   the Dockerfile builder.
3. Provision a **Volume** mounted at `/var/lib/odoo` so the filestore and
   sessions survive restarts. If you ship custom modules, mount a second
   volume at `/mnt/extra-addons`.
4. Deploy. The container binds to `$PORT` automatically.

## Environment variables

| Variable                | Default       | Notes                                                              |
| ----------------------- | ------------- | ------------------------------------------------------------------ |
| `DATABASE_URL`          | _(required)_  | Set by the Railway Postgres plugin                                 |
| `PORT`                  | `8069`        | Injected by Railway; the entrypoint forwards it to `--http-port`   |
| `ODOO_DATABASE`         | from URL      | Pin a single database name (recommended for production)            |
| `ODOO_INIT_MODULES`     | _(unset)_     | Comma-separated; installs and stops (use for first-boot bootstrap) |
| `ODOO_UPDATE_MODULES`   | _(unset)_     | Comma-separated; runs `-u` on boot                                 |
| `POSTGRES_WAIT_ATTEMPTS`| `30`          | Times to retry `pg_isready` before giving up                       |
| `POSTGRES_WAIT_DELAY`   | `2` seconds   | Delay between retries                                              |

## Initial database bootstrap

The first time you deploy, Odoo has no database yet. Two options:

- **Easy:** open the container shell from Railway and run
  `odoo -d <name> -i base --stop-after-init`, then redeploy.
- **Hands-off:** set `ODOO_INIT_MODULES=base` (and `ODOO_DATABASE=<name>`)
  for the first deploy, watch the logs, then unset the variable so
  subsequent boots don't try to reinstall.

## Local build / smoke test

```bash
docker build -t odoo-railway .
docker run --rm -p 8069:8069 \
    -e DATABASE_URL=postgresql://odoo:odoo@host.docker.internal:5432/odoo \
    odoo-railway
```
