{
    "name": "Website Mini Theme",
    "description": "A simple custom theme for Odoo website",
    "category": "Theme/Website",
    "version": "1.0",
    "author": "Your Name",
    "depends": ["website"],
    "data": [
        "views/layout_inherit.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "website_mini_theme/static/src/css/theme.scss",
        ],
    },
    "application": False,
    "installable": True,
    "license": "LGPL-3",
    "website_theme_install": True
}
