{
    "name": "Portal Rating",
    "version": "1.0",
    "category": "Services/Project",
    "description": """
Bridge module adding rating capabilities on portal. It includes notably
inclusion of rating directly within the customer portal discuss widget.
        """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "portal",
        "rating",
    ],
    "data": [
        "views/rating_rating_views.xml",
        "views/portal_templates.xml",
        "views/rating_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "portal_rating/static/src/scss/portal_rating.scss",
            "portal_rating/static/src/xml/portal_chatter.xml",
            "portal_rating/static/src/interactions/**/*",
            "portal_rating/static/src/xml/portal_rating_composer.xml",
            "portal_rating/static/src/xml/portal_tools.xml",
        ],
        "web.assets_unit_tests": [
            "portal_rating/static/tests/**/*.test.js",
        ],
        "web.assets_unit_tests_setup": [
            "portal_rating/static/src/interactions/**/*",
            "portal_rating/static/src/xml/**/*",
        ],
        "portal.assets_chatter": [
            "portal_rating/static/src/chatter/frontend/**/*",
        ],
        "portal.assets_chatter_style": [
            "portal_rating/static/src/scss/portal_rating.scss",
        ],
    },
    "auto_install": True,
}
