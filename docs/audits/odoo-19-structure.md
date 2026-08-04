# Odoo 19 Structure Audit

Date: 2026-08-04
Repository: `https://github.com/gentosai404/odoo`
Branch baseline: `19.0`
Baseline commit: `be685237124b4c645989811eac9b9ae115d1c8d9`

## Runtime

- Odoo: 19.0 final (`odoo/release.py`)
- Supported Python: 3.10 through 3.14
- Local Python: 3.11.15
- Minimum PostgreSQL: 13
- Local PostgreSQL: 18.4, accepting connections on `/var/run/postgresql:5432`
- Python environment: `/home/acer/.venvs/odoo19-gentosai`
- Native build prerequisites installed: `libldap2-dev`, `libsasl2-dev`, `libssl-dev`, `libpq-dev`
- `requirements.txt`: installed successfully
- `wkhtmltopdf`: absent; required later for PDF report rendering, not addon logic/tests

## Repository boundaries

- `odoo/`: server framework and ORM
- `addons/`: official Community addons; keep unchanged for maintainable upstream sync
- `custom_addons/`: Gentosai-owned addons
- `odoo-bin`: source-checkout launcher
- `requirements.txt`: version-gated Python dependencies
- `setup/`, `debian/`: packaging and deployment assets
- `doc/`: upstream documentation

## ERP components reused

- `product`: products, variants, units of measure
- `stock`: warehouses, locations, stock moves, inventory audit trail
- `mrp`: BOMs, Manufacturing Orders, work orders, material consumption, finished goods

Gentosai garment customization inherits `mrp.production`. It does not duplicate product, BOM, stock, or production-order models.

## Git remotes

- `origin`: `https://github.com/gentosai404/odoo.git`
- `upstream`: `https://github.com/odoo/odoo.git`

Custom work branch: `feat/gentosai-garment-workflow`.
