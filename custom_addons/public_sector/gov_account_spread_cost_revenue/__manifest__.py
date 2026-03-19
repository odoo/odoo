{
    "name": "AGI Gov - Accounting Spread Cost Revenue (Community)",
    "version": "19.0.1.0.0",
    "summary": "Deferred revenue and cost recognition across accounting periods",
    "category": "Accounting/Accounting",
    "author": "AGI Gov",
    "license": "LGPL-3",
    "depends": [
        "account",
        "mail",
        "gov_account_fiscal_year",
    ],
    "data": [
        "security/account_spread_groups.xml",
        "security/ir.model.access.csv",
        "data/account_spread_cron.xml",
        "views/account_spread_views.xml",
        "views/account_spread_line_views.xml",
        "views/account_move_views.xml",
        "views/account_spread_menus.xml",
    ],
    "installable": True,
    "application": False,
}
