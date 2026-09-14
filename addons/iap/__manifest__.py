{
    "name": "In-App Purchases",
    "version": "1.2",
    "category": "Hidden/Tools",
    "summary": "Basic models and helpers to support In-App purchases.",
    "description": """
This module provides standard tools (account model, context manager and helpers)
to support In-App purchases inside Odoo. """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "web",
        "credential",
    ],
    "data": [
        "data/services.xml",
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "views/iap_views.xml",
        "views/res_config_settings.xml",
        "views/iap_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "iap/static/src/**/*.js",
            "iap/static/src/**/*.xml",
        ],
    },
    "auto_install": True,
}
