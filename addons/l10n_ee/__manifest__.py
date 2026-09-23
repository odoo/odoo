{
    "name": "Estonia - Accounting",
    "version": "1.4",
    "category": "Accounting/Localizations/Account Charts",
    "description": """
This is the base module to manage the accounting chart for Estonia in Odoo.
    """,
    "author": "Odoo SA",
    "website": "https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations.html",
    "icon": "/account/static/description/l10n.png",
    "license": "LGPL-3",
    "depends": [
        "account",
        "account_edi_ubl_cii",
    ],
    "countries": [
        "ee",
    ],
    "data": [
        "security/ir.access.csv",
        "data/account_tax_report_data.xml",
        "views/account_tax_form.xml",
    ],
    "demo": [
        "demo/demo_company.xml",
    ],
    "auto_install": [
        "account",
    ],
}
