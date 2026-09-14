{
    "name": "OAuth2 Authentication",
    "version": "1.2",
    "category": "Hidden/Tools",
    "description": """
Allow users to login through OAuth2 Provider.
=============================================
""",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "auth_signup",
    ],
    "data": [
        "data/auth_oauth_data.xml",
        "views/auth_oauth_views.xml",
        "views/res_config_settings_views.xml",
        "views/auth_oauth_templates.xml",
        "security/ir.model.access.csv",
        "views/auth_oauth_menus.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "auth_oauth/static/**/*",
        ],
    },
}
