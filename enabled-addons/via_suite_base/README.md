# via_suite_base

Bootstraps ViaFronteira tenant databases with default settings:

- Keycloak SSO (auth_oauth provider + authorization_header=1)
- Active currencies: USD/BRL/ARS/PYG
- Company base currency: USD
- Pricelists A/B/C/D/E/F (global % discounts)
- Via roles/groups aligned with Sales/Stock/POS/Accounting
- Default admin users (SSO-ready)

## Keycloak configuration via environment variables

- VIA_KEYCLOAK_BASE_URL (e.g. http://k8s-development:32080)
- VIA_KEYCLOAK_REALM (e.g. viafronteira)
- VIA_KEYCLOAK_CLIENT_ID (e.g. via-suite)
- VIA_KEYCLOAK_CLIENT_SECRET (secret)
- VIA_KEYCLOAK_ENABLED (optional true/false)


createdb -h k8s-development -U odoo cliente1

VIA_KEYCLOAK_BASE_URL="http://k8s-development:32080" \
VIA_KEYCLOAK_REALM="viafronteira" \
VIA_KEYCLOAK_CLIENT_ID="via-suite" 
python3 odoo-bin -c odoo.conf -d cliente1 --without-demo=True -i via_suite_base --stop-after-init