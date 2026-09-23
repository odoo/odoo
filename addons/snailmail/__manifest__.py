{
    "name": "Snail Mail",
    "version": "0.5",
    "category": "Hidden/Tools",
    "description": """
Allows users to send documents by post
=====================================================
        """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "iap_mail",
        "mail",
    ],
    "data": [
        "data/iap_service_data.xml",
        "data/snailmail_data.xml",
        "views/report_assets.xml",
        "views/snailmail_views.xml",
        "security/ir.access.csv",
        "views/snailmail_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "snailmail/static/src/**/*",
        ],
        "snailmail.report_assets_snailmail": [
            (
                "include",
                "web._assets_helpers",
            ),
            "web/static/src/scss/pre_variables.scss",
            "web/static/lib/bootstrap/scss/_variables.scss",
            "web/static/lib/bootstrap/scss/_variables-dark.scss",
            "web/static/lib/bootstrap/scss/_maps.scss",
        ],
        "web.assets_unit_tests": [
            "snailmail/static/tests/**/*",
        ],
    },
    "esm": {
        "bundles": [
            "snailmail.report_assets_snailmail",
        ],
    },
    "auto_install": True,
}
