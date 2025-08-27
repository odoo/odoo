# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Sri Lanka - Accounting",
    "icon": "/account/static/description/l10n.png",
    "countries": ["lk"],
    "summary": "Provides accounting localizations for Sri Lanka.",
    "description": """
Sri Lankan Accounting module
============================
- Chart of Accounts
- Fiscal Position
- Taxes & Tax Groups

Forms
=====
- VAT001
- WHT001
    """,
    "version": "1.0",
    "author": "Odoo S.A.",
    "category": "Accounting/Localizations/Account Charts",
    "website": "https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations.html",
    "depends": [
        "account",
        "l10n_account_withholding_tax",
    ],
    "auto_install": ["account"],
    "data": [
        "data/form_vat001.xml",
        "data/form_wht001.xml",
    ],
    "demo": [
        "demo/demo_company.xml",
    ],
    "license": "LGPL-3",
}
