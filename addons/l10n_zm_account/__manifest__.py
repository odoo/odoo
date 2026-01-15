# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Zambia - Accounting",
    "countries": ["zm"],
    "version": "1.0.0",
    "category": "Accounting/Localizations/Account Charts",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "description": """
This is the basic Zambian localization necessary to run Odoo in ZM:
================================================================================
    - Chart of Accounts
    - Taxes
    - Fiscal Positions
    - Default Settings
    """,
    "depends": [
        "account",
    ],
    "auto_install": ["account"],
    "data": [
        "data/account_tax_report_data.xml",
        "views/report_invoice.xml",
    ],
    "demo": [
        "demo/demo_company.xml",
    ]
}
