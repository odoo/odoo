# -*- coding: utf-8 -*-
{
    "name": "CAMTEL Theme",
    "version": "1.0",
    "summary": "Custom CAMTEL login page theme with blue buttons and white text",
    "description": """
        Custom theme module for CAMTEL that provides:
        - Blue buttons with white text
        - Removal of Manage Databases option from login page
        - Changes "Powered by Odoo" to "Powered by Blue"
    """,
    "author": "CAMTEL",
    "website": "https://www.camtel.cm",
    "category": "Theme",
    "depends": ["web", "auth_signup"],
    "data": [
        "views/webclient_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "camtel_theme/static/src/scss/login_theme.scss",
        ],
        "web.assets_common": [
            "camtel_theme/static/src/scss/login_theme.scss",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
