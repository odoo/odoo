# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Sri Lanka - Accounting",
    "icon": "/account/static/description/l10n.png",
    "countries": ["lk"],
    "version": "1.0",
    "category": "Accounting/Localizations/Account Charts",
    "description": """
    Chart of Accounts and Taxes Sri Lanka.
    """,
    "website": "https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations.html",
    "depends": [
        "l10n_account_withholding_tax",
    ],
    "data": [
        "data/form_vat001.xml",
        "data/form_wht001.xml",
    ],
    "demo": [
        "demo/demo_company.xml",
    ],
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
