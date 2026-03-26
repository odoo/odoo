#!/usr/bin/env bash

set -euo pipefail

db="${1:-}"
domain="${2:-}"
check_public="${3:-1}"
local_origin="${4:-http://127.0.0.1:8069}"

if [[ -z "$db" ]]; then
  echo "Set DB=<tenant>."
  exit 1
fi

if [[ -z "$domain" ]]; then
  echo "Set DOMAIN."
  exit 1
fi

if ! printf '%s\n' "$db" | grep -Eq '^[a-z0-9][a-z0-9-]*$'; then
  echo "Invalid DB name '$db'."
  exit 1
fi

tenant_host="${db}.${domain}"
login_code="$(curl -I -s -H "Host: ${tenant_host}" "${local_origin}/web/login?db=${db}" | head -n 1 | cut -d' ' -f2 | tr -d '\r')"
if [[ "$login_code" != "200" ]]; then
  echo "FAIL: local tenant login returned HTTP ${login_code}."
  exit 1
fi

root_code="$(curl -I -s -H "Host: ${tenant_host}" "${local_origin}/" | head -n 1 | cut -d' ' -f2 | tr -d '\r')"
if [[ "$root_code" != "302" && "$root_code" != "303" ]]; then
  echo "FAIL: local tenant root returned HTTP ${root_code}."
  exit 1
fi

if [[ "$check_public" == "1" ]]; then
  public_code="$(curl -I -sS --max-time 20 "https://${tenant_host}" | head -n 1 | cut -d' ' -f2 | tr -d '\r' || true)"
  if [[ "$public_code" != "200" && "$public_code" != "301" && "$public_code" != "302" && "$public_code" != "303" ]]; then
    echo "FAIL: public tenant endpoint https://${tenant_host} returned HTTP ${public_code}."
    echo "INFO: Check Cloudflare Tunnel Public Hostname ${tenant_host} -> http://nginx:80"
    exit 1
  fi
  echo "OK: public tenant endpoint https://${tenant_host} -> HTTP ${public_code}."
else
  echo "Skipping public tenant endpoint check (TENANT_SMOKE_PUBLIC=0)."
fi

echo "Tenant smoke passed for ${tenant_host}."
