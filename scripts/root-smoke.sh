#!/usr/bin/env bash

set -euo pipefail

domain="${1:-}"
local_origin="${2:-http://127.0.0.1:8069}"

if [[ -z "$domain" ]]; then
  echo "Set DOMAIN."
  exit 1
fi

local_code="$(curl -I -s -H "Host: ${domain}" "${local_origin}/" | head -n 1 | cut -d' ' -f2 | tr -d '\r')"
if [[ "$local_code" != "200" && "$local_code" != "301" && "$local_code" != "302" && "$local_code" != "303" ]]; then
  echo "FAIL: local root host ${domain} returned HTTP ${local_code}."
  exit 1
fi
echo "OK: local root host ${domain} -> HTTP ${local_code}."

public_headers="$(curl -I -sS --max-time 20 "https://${domain}" || true)"
public_code="$(printf '%s\n' "$public_headers" | head -n 1 | cut -d' ' -f2 | tr -d '\r')"
if [[ -z "$public_code" ]]; then
  echo "FAIL: public root https://${domain} did not resolve or did not return headers."
  echo "INFO: publish ${domain} in Cloudflare Tunnel/DNS. Today only www may be present."
  exit 1
fi

if [[ "$public_code" != "200" && "$public_code" != "301" && "$public_code" != "302" && "$public_code" != "303" ]]; then
  echo "FAIL: public root https://${domain} returned HTTP ${public_code}."
  exit 1
fi

echo "OK: public root https://${domain} -> HTTP ${public_code}."
