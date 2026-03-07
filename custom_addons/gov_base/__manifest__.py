{
    "name": "GRP - Base Governamental",
    "version": "19.0.1.0.0",
    "category": "Government",
    "depends": ["base", "account"],
    "data": [
        "security/gov_base_groups.xml",
        "security/record_rules.xml",
        "security/ir.model.access.csv",
        "views/res_company_views.xml",
        "views/account_account_views.xml",
    ],
    "assets": {
        "web._assets_primary_variables": [
            "gov_base/static/src/scss/gov_variables.scss",
        ],
        "web.assets_backend": [
            "gov_base/static/src/scss/gov_dark_theme.scss",
        ],
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3",
    "author": "GRP",
}
