{
    "name": "Account Fiscal Year",
    "version": "19.0.1.0.0",
    "summary": "Manage fiscal years per company - Kore clean-room build",
    "description": "Kore fiscal year management for multi-company accounting periods.",
    "category": "Accounting/Accounting",
    "author": "Kore",
    "license": "LGPL-3",
    "depends": [
        "base",
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
    # kore-original - see SOURCES.md
}

