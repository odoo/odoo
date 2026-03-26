# Multi-Tenant Online

Recommended production contract:

- `kodoo.online` uses the primary database `kodoo`
- each tenant uses its own subdomain and database
- example: `semsa.kodoo.online` -> database `semsa`
- Odoo routing is based on `dbfilter = ^%d$`
- tenant maintenance targets must use the active production runtime topology
- when `CLOUDFLARED_TOKEN` is set, tenant targets operate through the tunnel compose overlay and local nginx bind on `127.0.0.1:8069`

Built-in tenant profiles:

- `TENANT_PORTAL_MODULES=base,web,mail,portal,auth_signup,website` is the shared frontend/auth baseline
- `TENANT_PROFILE=standard` installs `TENANT_PORTAL_MODULES`
- `TENANT_PROFILE=knowledge` installs `TENANT_PORTAL_MODULES,document_page,document_knowledge`
- `TENANT_PROFILE=gov` installs `TENANT_PORTAL_MODULES,gov_suite`
- `TENANT_BOOTSTRAP_MODULES=...` overrides the profile completely

Built-in tenant defaults:

- `TENANT_DEFAULT_LANG=pt_BR`
- `TENANT_DEFAULT_CURRENCY=BRL`
- `TENANT_COMPANY_NAME=<tenant>` when omitted
- `TENANT_ADMIN_LOGIN`, `TENANT_ADMIN_NAME`, and `TENANT_ADMIN_PASSWORD` are optional and only applied when provided

Operational flow for a new tenant:

```bash
make tenant-provision DB=semsa
```

Examples:

```bash
make tenant-provision DB=cliente-a TENANT_PROFILE=standard
make tenant-provision DB=cliente-docs TENANT_PROFILE=knowledge
make tenant-provision DB=semsa TENANT_PROFILE=gov
```

This target:

- ensures the tenant database exists
- installs the selected module pack when the database is still fresh
- fixes `web.base.url` to `https://<db>.kodoo.online`
- runs local isolation checks against PostgreSQL, tenant login routing, and the primary site
- keeps the root website on `kodoo.online`

Optional tenant bootstrap:

```bash
make tenant-provision DB=semsa TENANT_BOOTSTRAP_MODULES=base,web,mail
```

Post-provision module rollout:

```bash
make tenant-install-modules DB=semsa TENANT_BOOTSTRAP_MODULES=gov_knowledge_bridge
```

After that, publish the tenant hostname in Cloudflare Tunnel:

- Public Hostname: `semsa.kodoo.online`
- Type: `HTTP`
- URL: `http://nginx:80`

Quick checks:

```bash
make root-smoke
make tunnel-check SUBDOMAIN=semsa
make tenant-check DB=semsa
make tenant-smoke DB=semsa
make tenant-bootstrap-defaults DB=semsa TENANT_COMPANY_NAME='SEMSA'
make tenant-user-list DB=semsa
make tenant-user-password DB=semsa LOGIN=admin PASSWORD='new-secret'
```

Expected behavior:

- `https://kodoo.online` serves the root website from database `kodoo`
- `https://kodoo.kodoo.online` is treated as a canonical alias and redirects back to `https://kodoo.online`
- `https://semsa.kodoo.online` redirects to `/web/login?db=semsa`

Recommended onboarding sequence:

1. `make tenant-provision DB=<tenant> TENANT_PROFILE=<profile>`
2. Publish `<tenant>.kodoo.online` in Cloudflare Tunnel.
   If wildcard hostnames are not available in your panel, add one Public Hostname per tenant.
3. `make tenant-smoke DB=<tenant>`
4. `make tenant-install-modules DB=<tenant> TENANT_BOOTSTRAP_MODULES=<extras>` when that tenant needs a module pack beyond the base profile.

Post-provision tenant defaults:

- company name and company partner are aligned to the tenant identity
- `web.base.url` and `web.base.url.freeze` are enforced again
- admin login/name/password can be set if passed in the environment
- language and currency are normalized for the tenant

Portal behavior:

- internal users still land in `/odoo` after login
- portal users land in the frontend/portal flow once `portal` + `website` are installed
- if a tenant must behave like a client portal instead of a backoffice, create or downgrade the customer-facing accounts as portal users rather than internal users
