{
    "name": "Cloudflare Turnstile",
    "version": "1.1",
    "category": "Website/Website",
    "description": """
This module implements Cloudflare Turnstile so that you can prevent bot spam on your forms.
    """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "credential",
        "website",
    ],
    "data": [
        "views/res_config_settings_view.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "website_cf_turnstile/static/src/interactions/**/*.js",
            "website_cf_turnstile/static/src/interactions/**/*.xml",
        ],
        "web.assets_unit_tests": [
            "website_cf_turnstile/static/tests/**/*",
        ],
        "web.assets_unit_tests_setup": [
            "website_cf_turnstile/static/src/interactions/**/*.js",
            "website_cf_turnstile/static/src/interactions/**/*.xml",
        ],
    },
}
