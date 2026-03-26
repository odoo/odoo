#!/usr/bin/env bash

set -euo pipefail

db="${1:-}"

if [[ -z "$db" ]]; then
  echo "Set DB=<tenant>."
  exit 1
fi

docker exec kodoo-db psql -U kodoo -d "$db" -F ' | ' -Atc "
SELECT
  COALESCE(u.login, '<no-login>'),
  CASE WHEN u.share THEN 'portal' ELSE 'internal' END,
  COALESCE(p.email, '<no-email>'),
  COALESCE(p.name, '<no-name>'),
  CASE WHEN u.active THEN 'active' ELSE 'inactive' END
FROM res_users u
LEFT JOIN res_partner p ON p.id = u.partner_id
WHERE u.login NOT IN ('public', 'portaltemplate')
ORDER BY u.login;
"
