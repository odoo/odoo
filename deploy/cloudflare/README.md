# Cloudflare Tunnel Mode (No Certbot / No Public Ports)

Use this mode when your ISP is behind CGNAT or your IPv4 changes often.

## 1) Cloudflare side

1. Add `kodoo.online` to Cloudflare.
2. In HostGator, change nameservers to the 2 Cloudflare nameservers.
3. In Cloudflare Zero Trust, create a Tunnel and copy the token.
4. Add a Public Hostname in the tunnel:
   - Hostname: `kodoo.online` (and optionally `www.kodoo.online`)
   - Service type: `HTTP`
   - URL: `http://odoo:8069`

## 2) Local side

Set the tunnel token in shell:

```bash
export CLOUDFLARED_TOKEN='PASTE_YOUR_TUNNEL_TOKEN'
```

Start stack in Cloudflare mode:

```bash
make up-cloudflare
```

View tunnel logs:

```bash
make logs-cloudflare
```

Stop Cloudflare mode:

```bash
make down-cloudflare
```

## Notes

- In this mode, do not run `make certbot`.
- Public TLS is handled by Cloudflare.
- Keep host firewall without opening 80/443 to internet unless you still need local nginx for other reasons.
