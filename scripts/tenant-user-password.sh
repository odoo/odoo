#!/usr/bin/env bash

set -euo pipefail

db="${1:-}"
login="${2:-}"
password="${3:-}"

if [[ -z "$db" ]]; then
  echo "Set DB=<tenant>."
  exit 1
fi

if [[ -z "$login" ]]; then
  echo "Set LOGIN=<user login>."
  exit 1
fi

if [[ -z "$password" ]]; then
  echo "Set PASSWORD=<new password>."
  exit 1
fi

docker exec -i \
  -e KODOO_LOGIN="$login" \
  -e KODOO_PASSWORD="$password" \
  kodoo-odoo \
  odoo shell --no-http -c /etc/odoo/odoo.conf -d "$db" <<'PY'
import os

login = os.environ["KODOO_LOGIN"]
password = os.environ["KODOO_PASSWORD"]
users = env["res.users"].sudo().search(
    ["|", ("login", "=", login), ("partner_id.email", "=", login)],
    limit=2,
)
if not users:
    raise SystemExit(f"user not found by login or email: {login}")
if len(users) > 1:
    raise SystemExit(f"multiple users matched login/email: {login}")
user = users[0]
user.write({"password": password})
env.cr.commit()
print(f"password updated for {user.login} in {env.cr.dbname}")
PY
