# Infrastructure Runbook: Invoice Agent

This runbook documents the deployment, local testing, and update workflows for the `invoice_agent` module on the live EC2 environment and local development setups.

---

## 1. Environment Architecture & Bind Mounts

The Odoo container is configured to bind-mount the local addons directory directly into the container's extra addons path.

### `docker-compose.yml` snippet:
```yaml
services:
  db:
    image: postgres:16
    environment:
      - POSTGRES_DB=postgres
      - POSTGRES_USER=odoo
      - POSTGRES_PASSWORD=odoo
    volumes:
      - postgresql-data:/var/lib/postgresql/data

  odoo:
    image: odoo:19.0
    ports:
      - "8069:8069"
    environment:
      - HOST=db
      - USER=odoo
      - PASSWORD=odoo
    volumes:
      - ./addons:/mnt/extra-addons
      - odoo-web-data:/var/lib/odoo
    depends_on:
      - db