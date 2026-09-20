{
    "name": "Customer Rating",
    "version": "1.2",
    "category": "Productivity",
    "description": """
This module allows a customer to give rating.
""",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "mail",
    ],
    "data": [
        "views/rating_rating_views.xml",
        "views/rating_templates.xml",
        "views/mail_message_views.xml",
        "security/ir.model.access.csv",
        "views/rating_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "rating/static/src/core/common/**/*",
            "rating/static/src/core/web/**/*",
            "rating/static/src/scss/rating_rating_views.scss",
        ],
        "web.assets_frontend": [
            "rating/static/src/scss/rating_templates.scss",
        ],
        "web.assets_unit_tests": [
            "rating/static/tests/**/*",
        ],
        "mail.assets_public": [
            "rating/static/src/core/common/**/*",
        ],
        "portal.assets_chatter": [
            "rating/static/src/core/common/**/*",
        ],
    },
}
