{
    "name": "Madagascar - Accounting",
    "icon": "/account/static/description/l10n.png",
    "countries": ["mg"],
    "category": "Accounting/Localizations/Account Charts",
    "description": """
Chart of accounts, taxes, tax report and fiscal positions for Madagascar.
=========================================================================

The chart of accounts follows the Plan Comptable Général 2005 (PCG 2005).
    """,
    "website": "https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations.html",
    "depends": [
        "account",
    ],
    "auto_install": ["account"],
    "data": [
        "data/account_tax_report_data.xml",
        "views/report_templates.xml",
        "views/res_company_views.xml",
    ],
    "demo": [
        "demo/demo_company.xml",
    ],
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
