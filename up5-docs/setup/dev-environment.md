# Dev Environment Setup

**Stack:** Windows 11 + Miniconda + PostgreSQL + Git Bash

## Prerequisites

- [Miniconda](https://docs.conda.io/en/latest/miniconda.html)
- [PostgreSQL 16+](https://www.postgresql.org/download/windows/) — add `bin/` to PATH during install
- [Git for Windows](https://git-scm.com/download/win) — use Git Bash as your shell

## One-time setup

### 1. Clone the repo

```bash
git clone https://github.com/dgplex/odoo-up5.git
cd odoo-up5
git checkout 19.0
```

### 2. Create the conda environment

```bash
conda create -n odoo19 python=3.12 -y
conda activate odoo19
pip install wheel setuptools
pip install -r requirements.txt
```

### 3. Create the PostgreSQL role

```bash
psql -U postgres -c "CREATE ROLE odoo WITH LOGIN SUPERUSER PASSWORD 'odoo';"
```

### 4. Create `odoo.conf` at the repo root

> `odoo.conf` is gitignored — each developer creates their own locally.

```ini
[options]
addons_path = addons
db_host = localhost
db_port = 5432
db_user = odoo
db_password = odoo
db_name = odoo_dev
http_port = 8069
logfile = False
```

### 5. Initialise the database

```bash
conda activate odoo19
python odoo-bin -c odoo.conf -d odoo_dev --stop-after-init
```

## Daily workflow

```bash
conda activate odoo19
python odoo-bin -c odoo.conf --dev=all
```

Open http://localhost:8069 — login `admin` / `admin`.

## Running tests

```bash
# Preferred — runs lint + tests via verify.sh
./verify.sh <module>

# Tests only — all tests in a module
conda run -n odoo19 python odoo-bin -c odoo.conf \
  --test-enable -d odoo_dev --stop-after-init -i <module>

# Specific test class or method
conda run -n odoo19 python odoo-bin -c odoo.conf \
  --test-enable -d odoo_dev --stop-after-init -i <module> \
  --test-tags <module>/<ClassName>.<method_name>

# Verbose output
conda run -n odoo19 python odoo-bin -c odoo.conf \
  --test-enable -d odoo_dev --stop-after-init -i <module> \
  --log-level=test
```

Tests live in `addons/<module>/tests/test_*.py`.

## Lint only

```bash
conda run -n odoo19 ruff check addons/<module>/
```

`ruff` is configured in `ruff.toml` at repo root (Odoo's official rule set).

## Updating a module after code changes

```bash
conda run -n odoo19 python odoo-bin -c odoo.conf \
  -d odoo_dev --stop-after-init -u <module>
```
