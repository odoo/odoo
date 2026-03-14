{
    "name": "AGI Gov - Accounting Fiscal Year (Community)",
    "version": "19.0.1.0.0",
    "summary": "Manage fiscal years per company for accounting periods",
    "description": "Community-style fiscal year management aligned to GOV suite.",
    "category": "Accounting/Accounting",
    "author": "AGI Gov",
    "license": "LGPL-3",
    "depends": [
        "gov_base",
        "account",
    ],
    "data": [
        "security/account_fiscal_year_groups.xml",
        "security/ir.model.access.csv",
        "data/account_fiscal_year_sequence.xml",
        "views/account_fiscal_year_views.xml",
        "views/account_fiscal_year_menus.xml",
    ],
    "installable": True,
    "application": False,
}
