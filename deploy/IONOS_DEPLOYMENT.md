# Pushing to IONOS VPS

Quick reference for deploying and updating Odoo 18 on the IONOS VPS.

---

## Server Details

| Item | Value |
|------|-------|
| **Provider** | IONOS VPS (Cloud Server) |
| **OS** | Ubuntu |
| **User** | `root` |
| **Odoo Location** | `/opt/ovoco` |
| **Deploy Config** | `/opt/ovoco/deploy/` |
| **Nginx Config** | `/etc/nginx/sites-available/odoo` |

### Domains Hosted

| Domain | Type |
|--------|------|
| `books.ovoco.co` | Production (subdomain) |
| `test.ovoco.co` | Test / staging |
| `test.morelmediastudio.com` | Test / staging |
| `test.i84mobile.com` | Test / staging |
| `ovoco.co` / `www.ovoco.co` | Production |
| `property.ovoco.co` | Production (subdomain) |
| `morelmediastudio.com` / `www.morelmediastudio.com` | Production |
| `i84mobile.com` / `www.i84mobile.com` | Production |

---

## 1. SSH into the Server

```bash
ssh root@YOUR_VPS_IP
```

> Replace `YOUR_VPS_IP` with the actual IP from your IONOS Cloud Panel.

---

## 2. Push Code Updates

### Option A: Git Pull (Recommended)

From the VPS:

```bash
cd /opt/ovoco
git pull origin main      # or whatever branch you're deploying
```

If this is the first time, clone the repo:

```bash
cd /opt
git clone https://github.com/lindyjan/ovoco.git
cd ovoco
```

### Option B: SCP from Windows

From PowerShell on your local machine:

```powershell
# Push the whole project
scp -r C:\Projects\ovoco root@YOUR_VPS_IP:/opt/ovoco

# Or push just custom_addons (faster for module-only changes)
scp -r C:\Projects\ovoco\custom_addons root@YOUR_VPS_IP:/opt/ovoco/custom_addons
```

### Option C: rsync (Best for Incremental Updates)

```bash
# From your local machine (Git Bash or WSL)
rsync -avz --exclude='.git' --exclude='venv' --exclude='__pycache__' \
  /c/Projects/ovoco/ root@YOUR_VPS_IP:/opt/ovoco/
```

---

## 3. Rebuild and Restart Odoo

After pushing code changes:

```bash
cd /opt/ovoco/deploy

# Rebuild the Docker image (picks up new code/dependencies)
docker compose build

# Restart with the new image
docker compose up -d

# Watch the logs to confirm it started cleanly
docker compose logs -f odoo
```

Press `Ctrl+C` to stop following logs.

### Quick Restart (No Code Changes to Core Odoo)

If you only changed files in `custom_addons/` (which is bind-mounted), you
don't need to rebuild:

```bash
cd /opt/ovoco/deploy
docker compose restart odoo
```

---

## 4. Update a Specific Module

After pushing module changes, tell Odoo to reload it:

```bash
cd /opt/ovoco/deploy

# Update a single module
docker compose exec odoo odoo --config=/etc/odoo/odoo.conf \
  -d YOUR_DATABASE_NAME -u your_module_name --stop-after-init

# Update multiple modules
docker compose exec odoo odoo --config=/etc/odoo/odoo.conf \
  -d YOUR_DATABASE_NAME -u module1,module2 --stop-after-init

# Restart after updating
docker compose restart odoo
```

> Replace `YOUR_DATABASE_NAME` with your actual Odoo database name.

---

## 5. Multisite Nginx Setup

The server runs multiple domains through a single Odoo instance, each with its
own nginx server block. The config is at `/etc/nginx/sites-available/odoo`.

### How It Works

- All domains proxy to `127.0.0.1:8069` (Odoo) and `127.0.0.1:8072` (websocket/longpolling)
- Each domain has an HTTP block (port 80) that redirects to HTTPS
- Each domain has an HTTPS block (port 443) with its own SSL certificate
- Odoo uses `dbfilter` or manual database selection to serve the right database per domain

### Editing the Nginx Config

```bash
nano /etc/nginx/sites-available/odoo
```

### After Making Changes

```bash
# Test the config for syntax errors
nginx -t

# If the test passes, reload nginx
systemctl reload nginx
```

### Adding a New Domain

1. Point the domain's DNS A record to your VPS IP address (in IONOS DNS settings or your registrar)
2. Add server blocks to the nginx config:

```nginx
# HTTP -> HTTPS redirect
server {
    listen 80;
    server_name newdomain.com www.newdomain.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS server block
server {
    listen 443 ssl http2;
    server_name newdomain.com www.newdomain.com;

    # SSL certs (certbot will fill these in)
    ssl_certificate /etc/letsencrypt/live/newdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/newdomain.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    proxy_read_timeout 720s;
    proxy_connect_timeout 720s;
    proxy_send_timeout 720s;

    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Real-IP $remote_addr;

    access_log /var/log/nginx/newdomain.access.log;
    error_log /var/log/nginx/newdomain.error.log;

    location /websocket {
        proxy_pass http://127.0.0.1:8072;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location / {
        proxy_redirect off;
        proxy_pass http://127.0.0.1:8069;
    }

    location ~* /web/static/ {
        proxy_cache_valid 200 90m;
        proxy_buffering on;
        expires 864000;
        proxy_pass http://127.0.0.1:8069;
    }

    gzip_types text/css text/plain text/xml application/xml application/javascript application/json;
    gzip on;

    client_max_body_size 200m;
}
```

3. Get an SSL certificate:

```bash
certbot --nginx -d newdomain.com -d www.newdomain.com
```

4. Test and reload:

```bash
nginx -t && systemctl reload nginx
```

5. Create a new Odoo database for the domain (or use the same one).

---

## 6. SSL Certificate Management

Certificates are managed by Let's Encrypt via certbot.

```bash
# Check current certificates
certbot certificates

# Renew all certificates (dry run first)
certbot renew --dry-run

# Actually renew
certbot renew

# Add SSL to a new domain
certbot --nginx -d newdomain.com -d www.newdomain.com
```

Certbot sets up automatic renewal via a systemd timer. Verify it's active:

```bash
systemctl status certbot.timer
```

---

## 7. Database Backup and Restore

### Backup

```bash
cd /opt/ovoco/deploy

# Backup a specific database
docker compose exec db pg_dump -U odoo YOUR_DATABASE_NAME > ~/backup_$(date +%F).sql

# Backup all databases
docker compose exec db pg_dumpall -U odoo > ~/backup_all_$(date +%F).sql
```

### Restore

```bash
cd /opt/ovoco/deploy

# Restore a specific database
docker compose exec -T db psql -U odoo YOUR_DATABASE_NAME < ~/backup_2025-01-15.sql
```

### Backup Odoo Filestore

The filestore (uploaded files, attachments) lives in a Docker volume:

```bash
# Find the volume path
docker volume inspect ovoco_odoo-web-data

# Copy the filestore to a backup location
docker cp odoo18-app:/var/lib/odoo ~/odoo-filestore-backup
```

---

## 8. Viewing Logs

```bash
cd /opt/ovoco/deploy

# Follow Odoo logs
docker compose logs -f odoo

# Follow database logs
docker compose logs -f db

# Last 100 lines
docker compose logs --tail=100 odoo

# Nginx logs
tail -f /var/log/nginx/odoo.access.log
tail -f /var/log/nginx/odoo.error.log
```

---

## 9. Common Operations Cheat Sheet

```bash
# SSH in
ssh root@YOUR_VPS_IP

# Pull latest code and redeploy
cd /opt/ovoco && git pull && cd deploy && docker compose build && docker compose up -d

# Quick restart (custom_addons changes only)
cd /opt/ovoco/deploy && docker compose restart odoo

# Check what's running
docker compose ps

# Stop everything
docker compose down

# Stop everything AND delete data (careful!)
docker compose down -v

# Check disk space
df -h

# Check memory usage
free -h

# Check running processes
htop
```

---

## 10. Typical Deploy Workflow

Here's the full workflow from making changes locally to seeing them live:

1. **Develop locally** on Windows with VS Code
2. **Test locally** at `http://localhost:8069`
3. **Commit and push** to GitHub:
   ```powershell
   cd C:\Projects\ovoco
   git add .
   git commit -m "describe your changes"
   git push origin main
   ```
4. **SSH into the VPS**:
   ```bash
   ssh root@YOUR_VPS_IP
   ```
5. **Pull and deploy**:
   ```bash
   cd /opt/ovoco
   git pull origin main
   cd deploy
   docker compose build    # skip if only custom_addons changed
   docker compose up -d
   ```
6. **Update modules if needed**:
   ```bash
   docker compose exec odoo odoo --config=/etc/odoo/odoo.conf \
     -d YOUR_DATABASE_NAME -u your_module_name --stop-after-init
   docker compose restart odoo
   ```
7. **Verify** by visiting your domain in the browser
