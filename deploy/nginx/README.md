# Legacy Nginx + Certbot Reference

The direct public-IP + certbot flow is currently disabled in this project.

For public internet publishing, use Cloudflare Tunnel instead:

```bash
make up-tunnel
make logs-tunnel
make down-tunnel
```

Notes:

- Public TLS is handled by Cloudflare in the supported flow.
- Keep `80/443` closed to the internet when using tunnel mode.
- This file remains only as historical reference in case direct TLS is re-enabled later.
