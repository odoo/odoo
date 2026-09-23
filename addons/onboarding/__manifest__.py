{
    "name": "Onboarding Toolbox",
    "version": "1.2",
    "category": "Hidden",
    "sequence": 9001,
    "description": """
This module allows to manage onboardings and their progress
================================================================================
    """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "web",
    ],
    "data": [
        "views/onboarding_templates.xml",
        "views/onboarding_views.xml",
        "views/onboarding_menus.xml",
        "security/ir.access.csv",
    ],
    "assets": {
        "web.assets_backend": [
            "onboarding/static/src/**/*",
        ],
        "web._assets_primary_variables": [
            "onboarding/static/src/scss/onboarding.variables.scss",
        ],
    },
}
