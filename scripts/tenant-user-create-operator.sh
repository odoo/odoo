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
  echo "Set LOGIN=<operator email/login>."
  exit 1
fi

if [[ -z "$name" ]]; then
  echo "Set NAME=<operator display name>."
  exit 1
fi

if [[ -z "$password" ]]; then
  echo "Set PASSWORD=<operator password>."
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

internal_group = env.ref("base.group_user").sudo()
system_group = env.ref("base.group_system").sudo()

users = user_model.search(
    ["|", ("login", "=", login), ("partner_id.email", "=", login)],
    limit=2,
)
if len(users) > 1:
    raise SystemExit(f"multiple users matched login/email: {login}")

if users:
    user = users[0]
    partner = user.partner_id
    partner.write({"name": name, "email": login})
    user.write({
        "login": login,
        "password": password,
        "group_ids": [(6, 0, [internal_group.id, system_group.id])],
        "share": False,
        "active": True,
    })
    action = "operator user updated"
else:
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
        "group_ids": [(6, 0, [internal_group.id, system_group.id])],
        "share": False,
        "active": True,
    })
    action = "operator user created"

env.cr.commit()
print(f"{action} for {user.login} in {env.cr.dbname}")
PY
