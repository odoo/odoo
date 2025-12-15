{
    "name": "Via Suite Base",
    "summary": "Bootstrap defaults for ViaFronteira tenants (Keycloak SSO, currencies, USD base, pricelists, roles, admin users).",
    "description": """
Via Suite Base
==============

Seeds a new tenant database with ViaFronteira defaults:

- System parameters (e.g., auth_oauth.authorization_header)
- Keycloak OAuth provider skeleton (auth.oauth.provider)
- Currency activation: USD/BRL/ARS/PYG
- Company base currency default: USD
- Wholesale pricing tiers: Pricelists A/B/C/D/E/F
- Via roles/groups aligned to Odoo core apps (Sales/Stock/POS/Accounting)
- Default admin users (SSO-ready)

Secrets are injected via environment variables in post_init_hook (no secrets in Git).
    """,
    "author": "ViaFronteira",
    "website": "https://viafronteira.com",
    "category": "ViaFronteira",
    "version": "19.0.1.0.0",
    "license": "LGPL-3",
    "depends": [
        "base",
        "auth_oauth",

        # Required for groups and pricelists seeds:
        "product",
        "sale_management",
        "stock",
        "point_of_sale",
        "account",
    ],
    "data": [
        "data/ir_config_parameter.xml",
        "data/auth_oauth_provider.xml",

        "data/currencies.xml",
        "data/company.xml",

        "data/pricelists.xml",
        "data/groups.xml",
        "data/users.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}