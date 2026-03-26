#!/usr/bin/env bash

set -euo pipefail

db="${1:-}"
base_url="${2:-}"
company_name="${3:-}"
admin_login="${4:-}"
admin_password="${5:-}"
admin_name="${6:-}"
lang_code="${7:-pt_BR}"
currency_code="${8:-BRL}"

if [[ -z "$db" ]]; then
  echo "Set DB=<tenant>."
  exit 1
fi

if [[ -z "$base_url" ]]; then
  echo "Set BASE_URL."
  exit 1
fi

if [[ -z "$company_name" ]]; then
  company_name="${db}"
fi

docker exec -i \
  -e KODOO_BASE_URL="$base_url" \
  -e KODOO_COMPANY_NAME="$company_name" \
  -e KODOO_ADMIN_LOGIN="$admin_login" \
  -e KODOO_ADMIN_PASSWORD="$admin_password" \
  -e KODOO_ADMIN_NAME="$admin_name" \
  -e KODOO_LANG_CODE="$lang_code" \
  -e KODOO_CURRENCY_CODE="$currency_code" \
  kodoo-odoo \
  odoo shell --no-http -c /etc/odoo/odoo.conf -d "$db" <<'PY'
import os

base_url = os.environ["KODOO_BASE_URL"].strip()
company_name = os.environ["KODOO_COMPANY_NAME"].strip()
admin_login = os.environ["KODOO_ADMIN_LOGIN"].strip()
admin_password = os.environ["KODOO_ADMIN_PASSWORD"].strip()
admin_name = os.environ["KODOO_ADMIN_NAME"].strip()
lang_code = os.environ["KODOO_LANG_CODE"].strip() or "pt_BR"
currency_code = os.environ["KODOO_CURRENCY_CODE"].strip() or "BRL"

params = env["ir.config_parameter"].sudo()
params.set_param("web.base.url", base_url)
params.set_param("web.base.url.freeze", "True")

company = env.company.sudo()
company.write({"name": company_name})
if company.partner_id:
    company.partner_id.write({"name": company_name})

lang = env["res.lang"].sudo().search([("code", "=", lang_code)], limit=1)
if lang:
    if not lang.active:
        lang.write({"active": True})
    company.write({"partner_id": company.partner_id.id})
    company.partner_id.write({"lang": lang.code})

currency = env["res.currency"].sudo().search([("name", "=", currency_code)], limit=1)
if currency:
    company.write({"currency_id": currency.id})

admin = env.ref("base.user_admin").sudo()
admin_updates = {}
if admin_login:
    admin_updates["login"] = admin_login
if admin_name:
    admin.partner_id.write({"name": admin_name})
if lang:
    admin.partner_id.write({"lang": lang.code})
if admin_updates:
    admin.write(admin_updates)
if admin_password:
    admin.write({"password": admin_password})

if "website" in env:
    websites = env["website"].sudo().search([])
    for website in websites:
        updates = {}
        if hasattr(website, "domain"):
            updates["domain"] = base_url
        if hasattr(website, "name") and company_name:
            updates["name"] = company_name
        if updates:
            website.write(updates)

env.cr.commit()
print(f"tenant defaults applied to {env.cr.dbname}")
print(f"base_url={base_url}")
print(f"company={company.name}")
print(f"lang={lang.code if lang else 'n/a'}")
print(f"currency={currency.name if currency else 'n/a'}")
print(f"admin_login={admin.login}")
PY
