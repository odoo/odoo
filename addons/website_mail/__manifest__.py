{
    "name": "Website Mail",
    "version": "0.1",
    "category": "Website/Website",
    "summary": "Website Module for Mail",
    "description": """
Module holding mail improvements for website. It holds the follow widget.
""",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "website",
        "mail",
    ],
    "data": [
        "views/website_mail_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "website_mail/static/src/interactions/follow.js",
            "website_mail/static/src/css/website_mail.scss",
        ],
        "web.assets_inside_builder_iframe": [
            "website_mail/static/src/interactions/follow.edit.js",
        ],
        "web.assets_unit_tests_setup": [
            "website_mail/static/src/interactions/follow.js",
        ],
        "web.assets_unit_tests": [
            "website_mail/static/tests/**/*.test.js",
        ],
    },
    "auto_install": True,
}
