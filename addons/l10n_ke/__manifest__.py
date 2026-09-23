{
    "name": "Kenya - Accounting",
    "version": "1.0",
    "category": "Accounting/Localizations/Account Charts",
    "description": """
This provides a base chart of accounts and taxes template for use in Odoo.
    """,
    "author": "Odoo S.A.",
    "website": "https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations/kenya.html",
    "icon": "/account/static/description/l10n.png",
    "license": "LGPL-3",
    "depends": [
        "account",
    ],
    "countries": [
        "ke",
    ],
    "data": [
        "views/account_move_views.xml",
        "views/account_tax_views.xml",
        "views/l10n_ke_item_code_views.xml",
        "data/l10n_ke.item.code.csv",
        "data/account_tax_report_data.xml",
        "data/account_wh_tax_report_data.xml",
        "security/ir.access.csv",
    ],
    "demo": [
        "demo/demo_company.xml",
    ],
    "auto_install": [
        "account",
    ],
}
