# -*- coding: utf-8 -*-
{
    "name": "My Theme Deeper",
    "summary": "Backend-only Deeper Signals palette and typography",
    "version": "19.0.0.0.0",
    "category": "Theme/Backend",
    "author": "GRP",
    "depends": ["web"],
    "assets": {
        "web.assets_backend": [
            (
                "before",
                "web/static/src/scss/primary_variables.scss",
                "my_theme_deeper/static/src/scss/colors.scss",
            ),
            (
                "before",
                "web/static/src/scss/primary_variables.scss",
                "my_theme_deeper/static/src/scss/fonts.scss",
            ),
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}

