#!/bin/bash
set -e

# Start PostgreSQL via Docker (only if not running)
docker ps | grep pg-odoo > /dev/null || docker run --name pg-odoo \
  -e POSTGRES_USER=odoo -e POSTGRES_PASSWORD=odoo -e POSTGRES_DB=postgres \
  -p 5432:5432 -d postgres:13

# Install common dependencies
pip install -q --upgrade pip
pip install -q chardet pyOpenSSL rjsmin rcssmin Babel libsass pyjwt num2words passlib werkzeug==2.2.0

# Create custom_addons folder if not exist
mkdir -p custom_addons

# Start Odoo
./odoo-bin -d odoo_db \
  --db_host=localhost \
  --db_port=5432 \
  --db_user=odoo \
  --db_password=odoo \
  --addons-path=addons,custom_addons \
  -i base
