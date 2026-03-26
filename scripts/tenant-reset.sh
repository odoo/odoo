#!/usr/bin/env bash

set -euo pipefail

db="${1:-}"
owner="${2:-kodoo}"
primary_db="${3:-kodoo}"

if [[ -z "$db" ]]; then
  echo "Set DB=<tenant>."
  exit 1
fi

if [[ "$db" == "$primary_db" ]]; then
  echo "Refusing reset of primary DB ${primary_db}."
  exit 1
fi

docker exec kodoo-db psql -U "$owner" -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${db}' AND pid <> pg_backend_pid();" >/dev/null
docker exec kodoo-db psql -U "$owner" -d postgres -c "DROP DATABASE IF EXISTS \"${db}\";"
echo "Tenant database '${db}' dropped."
