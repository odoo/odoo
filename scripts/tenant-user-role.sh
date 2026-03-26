#!/usr/bin/env bash

set -euo pipefail

db="${1:-}"
login="${2:-}"
role="${3:-}"

if [[ -z "$db" ]]; then
  echo "Set DB=<tenant>."
  exit 1
fi

if [[ -z "$login" ]]; then
  echo "Set LOGIN=<user login or email>."
  exit 1
fi

case "$role" in
  portal|internal) ;;
  *)
    echo "Set ROLE=portal|internal."
    exit 1
    ;;
esac

docker exec -i \
  -e KODOO_LOGIN="$login" \
  -e KODOO_ROLE="$role" \
  kodoo-odoo \
  odoo shell --no-http -c /etc/odoo/odoo.conf -d "$db" <<'PY'
import os

identifier = os.environ["KODOO_LOGIN"].strip()
role = os.environ["KODOO_ROLE"].strip()

users = env["res.users"].sudo().search(
    ["|", ("login", "=", identifier), ("partner_id.email", "=", identifier)],
    limit=2,
)
if not users:
    raise SystemExit(f"user not found by login or email: {identifier}")
if len(users) > 1:
    raise SystemExit(f"multiple users matched login/email: {identifier}")

user = users[0]
if user.login == "__system__":
    raise SystemExit("refusing to change role for __system__")

portal_group = env.ref("base.group_portal").sudo()
internal_group = env.ref("base.group_user").sudo()
if role == "portal":
    user.write({"group_ids": [(6, 0, [portal_group.id])], "share": True, "active": True})
else:
    user.write({"group_ids": [(6, 0, [internal_group.id])], "share": False, "active": True})

env.cr.commit()
print(
    f"user role updated for {user.login} in {env.cr.dbname}: "
    f"role={role} internal={user.has_group('base.group_user')} "
    f"portal={user.has_group('base.group_portal')} share={user.share}"
)
PY
