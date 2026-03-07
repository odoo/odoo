# Nginx + TLS (Let's Encrypt) for kodoo.online

This setup keeps Odoo private and exposes only ports `80/443` through Nginx.

## 1) DNS prerequisite

Create these records at your DNS provider:

- `A` record: `kodoo.online` -> `<YOUR_SERVER_PUBLIC_IP>`
- `CNAME` record: `www` -> `kodoo.online`

## 2) Start application stack

From repository root:

```bash
docker compose up -d db odoo nginx ollama
```

Nginx starts in HTTP mode until a certificate exists.

## 3) Issue first certificate

Replace `EMAIL` with your email:

```bash
docker compose --profile certbot run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  -d kodoo.online -d www.kodoo.online \
  --email EMAIL --agree-tos --no-eff-email
```

Then restart Nginx to load HTTPS config:

```bash
docker compose restart nginx
```

## 4) Renewal

Run periodically (for example via cron):

```bash
docker compose --profile certbot run --rm certbot renew --webroot -w /var/www/certbot
docker compose exec nginx nginx -s reload
```

## 5) Security notes

- Keep host firewall open only for `80`, `443`, and restricted `22` (SSH).
- Do not expose `8069`, `8072`, `5432`, or `11434` publicly.
- Update `deploy/odoo/kodoo.prod.conf` and set a strong `admin_passwd`.
