# Infrastructure Reference — KSW Odoo

## Architecture

| Environment | How it runs | Port | Database | Code |
|---|---|---|---|---|
| **Production** | Docker container (`kswco-prod` project) | host:**8069** | `KSWCO` (host PostgreSQL) | Baked into image at build time |
| **Dev** | systemd service `odoo-dev` (bare-metal) | localhost:**8070** | `odoo_dev` (host PostgreSQL) | Live from repo — edit and restart |

Only **one Docker container exists** — production. Dev runs as a normal local process
(`odoo-bin -c KSW_dev.conf`) under systemd so you can edit files in
`custom_addons/KSW/` and see changes immediately after a restart/upgrade, with zero risk
of touching the production container.

- Production data dir: `/home/odoo/.local/share/Odoo` (mounted into the container)
- Dev data dir: `/home/odoo/.local/share/Odoo-dev` (filestore cloned from prod once;
  diverges over time as you test in dev)
- Dev config: `/home/odoo/Odoo/odoo/KSW_dev.conf`
- Prod config: baked from `.env.prod` into the container's environment

---

## Production (Docker)

All commands run from `/home/odoo/Odoo/odoo`.

### Alias

```bash
alias dc-prod='docker compose -p kswco-prod -f docker-compose.yml -f docker-compose.prod.yml'
```

### Start / stop / restart

```bash
dc-prod up -d            # start
dc-prod down              # stop
dc-prod restart odoo      # restart without recreating
```

### Logs

```bash
dc-prod logs -f odoo
```

### Module upgrade

```bash
dc-prod run --rm odoo odoo -u KSW_attendance_leave -d KSWCO --stop-after-init
dc-prod up -d              # bring it back up after --stop-after-init exits
```

### Deploy a code change to production

Production addons are baked into the image at build time — there are no bind-mounts,
no hot reload. This is the only way to ship a change to prod:

```bash
# 1. Build new image (snapshots current custom_addons/)
docker build -t ghcr.io/mohammedj-sadiq/kswco-odoo:latest .

# 2. Push to registry
docker push ghcr.io/mohammedj-sadiq/kswco-odoo:latest

# 3. Recreate the prod container with the new image
dc-prod up -d --force-recreate

# 4. If XML views or models changed, upgrade the affected module(s)
dc-prod run --rm odoo odoo -u KSW_attendance_leave -d KSWCO --stop-after-init
dc-prod up -d
```

### Shell into the container

```bash
dc-prod exec odoo bash
```

---

## Dev (systemd, bare-metal)

Dev is a normal Python process managed by systemd — no Docker involved. Code changes
in `custom_addons/KSW/` take effect on the next restart (Python) or module upgrade
(XML/data).

### Start / stop / restart

```bash
sudo systemctl start odoo-dev
sudo systemctl stop odoo-dev
sudo systemctl restart odoo-dev
sudo systemctl status odoo-dev
```

### Logs

```bash
journalctl -u odoo-dev -f
```

### Module upgrade

```bash
sudo systemctl stop odoo-dev
/home/odoo/odoo19env/bin/python3.12 /home/odoo/Odoo/odoo/odoo-bin \
  -c /home/odoo/Odoo/odoo/KSW_dev.conf -u KSW_attendance_leave --stop-after-init
sudo systemctl start odoo-dev
```

### Access

Browser: `http://localhost:8070` (or via SSH tunnel if remote).
Master/admin password is the same hash as production (`KSW_dev.conf` matches
`KSW.conf`).

### Refreshing dev data from production

Dev's `odoo_dev` database and filestore are a one-time clone of `KSWCO`/prod filestore.
To re-sync dev with the latest production data:

```bash
sudo systemctl stop odoo-dev
dropdb -U odoo odoo_dev
createdb -U odoo odoo_dev -O odoo
pg_dump -U odoo KSWCO | psql -U odoo odoo_dev
rm -rf /home/odoo/.local/share/Odoo-dev/filestore/odoo_dev
cp -r /home/odoo/.local/share/Odoo/filestore/KSWCO /home/odoo/.local/share/Odoo-dev/filestore/odoo_dev
sudo systemctl start odoo-dev
```

> If `KSWCO` has active connections, `dropdb`/`createdb -T` will fail — the
> `dropdb`+`createdb`+`pg_dump | psql` sequence above works on a live source database.

---

## Quick Reference Card

| Action | Dev | Prod |
|---|---|---|
| Start | `sudo systemctl start odoo-dev` | `dc-prod up -d` |
| Stop | `sudo systemctl stop odoo-dev` | `dc-prod down` |
| Restart | `sudo systemctl restart odoo-dev` | `dc-prod restart odoo` |
| Logs | `journalctl -u odoo-dev -f` | `dc-prod logs -f odoo` |
| Status | `systemctl status odoo-dev` | `docker ps` |
| Upgrade module | stop → run with `-u MODULE --stop-after-init` → start | `dc-prod run --rm odoo odoo -u MODULE -d KSWCO --stop-after-init` |
| Deploy code | edit files, restart/upgrade — immediate | rebuild image, push, `up -d --force-recreate` |

> `dc-prod` is the alias defined above.
