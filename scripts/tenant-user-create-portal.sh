#!/usr/bin/env bash

set -euo pipefail

db="${1:-}"
login="${2:-}"
name="${3:-}"
password="${4:-}"

if [[ -z "$db" ]]; then
  echo "Set DB=<tenant>."
  exit 1
fi

if [[ -z "$login" ]]; then
  echo "Set LOGIN=<portal email/login>."
  exit 1
fi

if [[ -z "$name" ]]; then
  echo "Set NAME=<portal display name>."
  exit 1
fi

if [[ -z "$password" ]]; then
  echo "Set PASSWORD=<portal password>."
  exit 1
fi

docker exec -i \
  -e KODOO_LOGIN="$login" \
  -e KODOO_NAME="$name" \
  -e KODOO_PASSWORD="$password" \
  kodoo-odoo \
  odoo shell --no-http -c /etc/odoo/odoo.conf -d "$db" <<'PY'
import os

login = os.environ["KODOO_LOGIN"].strip()
name = os.environ["KODOO_NAME"].strip()
password = os.environ["KODOO_PASSWORD"].strip()

user_model = env["res.users"].sudo()
partner_model = env["res.partner"].sudo()
portal_group = env.ref("base.group_portal").sudo()

existing = user_model.search(["|", ("login", "=", login), ("partner_id.email", "=", login)], limit=1)
if existing:
    raise SystemExit(f"user already exists: {existing.login}")

partner = partner_model.search([("email", "=", login)], limit=1)
if not partner:
    partner = partner_model.create({"name": name, "email": login})
else:
    partner.write({"name": name, "email": login})

user = user_model.create({
    "name": name,
    "login": login,
    "password": password,
    "partner_id": partner.id,
    "group_ids": [(6, 0, [portal_group.id])],
    "share": True,
    "active": True,
})
partner.signup_prepare()
env.cr.commit()

print(f"portal user created for {user.login} in {env.cr.dbname}")
PY
