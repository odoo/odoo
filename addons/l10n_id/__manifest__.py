{
    "name": "Indonesian - Accounting",
    "version": "1.3",
    "category": "Accounting/Localizations/Account Charts",
    "description": """
This is the latest Indonesian Odoo localisation necessary to run Odoo accounting for SMEs with:
=================================================================================================
    - generic Indonesian chart of accounts
    - tax structure""",
    "author": "vitraining.com",
    "website": "https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations/indonesia.html",
    "icon": "/account/static/description/l10n.png",
    "license": "LGPL-3",
    "depends": [
        "account",
        "account_iban",
        "account_vat",
    ],
    "countries": [
        "id",
    ],
    "data": [
        "security/ir.access.csv",
        "data/ir_cron.xml",
        "views/account_move_views.xml",
        "views/res_bank.xml",
    ],
    "demo": [
        "demo/demo_company.xml",
    ],
    "auto_install": [
        "account",
    ],
}
