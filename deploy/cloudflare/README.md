# Cloudflare Tunnel Mode (Supported Public Publishing Path)

Use this mode when your ISP is behind CGNAT or your IPv4 changes often.

## 1) Cloudflare side

1. Add `kodoo.online` to Cloudflare.
2. In HostGator, change nameservers to the 2 Cloudflare nameservers.
3. In Cloudflare Zero Trust, create a Tunnel and copy the token.
4. Add Public Hostnames in the tunnel:
   - Root app:
     - Hostname: `kodoo.online` (and optionally `www.kodoo.online`)
     - Service type: `HTTP`
     - URL: `http://nginx:80`
   - Multi-tenant subdomains:
     - Preferred: wildcard hostname `*.kodoo.online`
     - Service type: `HTTP`
     - URL: `http://nginx:80`
     - This is required when Odoo uses `dbfilter = ^%d$` and tenants are mapped by subdomain, for example `semsa.kodoo.online` -> database `semsa`.

## 2) Local side

Set the tunnel token in `.env` (preferred; legacy `.env.make` still works) or export it in shell:

```bash
CLOUDFLARED_TOKEN='PASTE_YOUR_TUNNEL_TOKEN'
```

Start the supported public stack:

```bash
make up-tunnel
```

View tunnel logs:

```bash
make logs-tunnel
```

Stop Cloudflare mode:

```bash
make down-tunnel
```

## Notes

- `certbot` and direct/public-IP TLS flow are disabled for now.
- Public TLS is handled by Cloudflare.
- Keep host firewall without opening 80/443 to the internet for this mode.
- If `https://kodoo.online` works but `https://tenant.kodoo.online` does not resolve, the missing piece is on the Cloudflare Tunnel side, not in Odoo/PostgreSQL.
