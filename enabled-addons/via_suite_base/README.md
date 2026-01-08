ViaSuite Base Module
====================

        Core module providing base customizations for ViaSuite:
        
        Features:
        ---------
        * Multi-language support (pt_BR, es_PY, en_US, ar_SA, zh_CN)
        * Keycloak SSO integration (multi-tenant)

        This module is auto-installed and provides the foundation for all
        ViaSuite tenants.

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