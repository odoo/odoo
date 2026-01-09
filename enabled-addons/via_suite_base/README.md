ViaSuite Base Module
====================

        Core module providing base customizations for ViaSuite:
        
        Features:
        ---------
        * **Keycloak SSO integration**: Core authentication logic for multi-tenant environments.
        * **Tenant Validation**: Ensures users can only access their designated tenant database.
        * **Branded Login UI**: Customized Odoo 19 login pages with ViaSuite identity.
        * **Multi-language support**: pt_BR, es_PY, en_US, ar_SA, zh_CN.

        This module is the core foundation and is installed in **every** tenant database. For central redirection and global management, see `via_suite_portal`.

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