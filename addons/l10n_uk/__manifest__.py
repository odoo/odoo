# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'United Kingdom - Accounting',
    'version': '1.0',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This is the latest UK Odoo localisation necessary to run Odoo accounting for UK SME's with:
=================================================================================================
    - a CT600-ready chart of accounts
    - VAT100-ready tax structure
    - InfoLogic UK counties listing
    - a few other adaptations""",
    'author': 'SmartMode LTD',
    'website': 'https://www.odoo.com/app/accounting',
    'depends': [
        'account',
        'base_iban',
        'base_vat',
    ],
    'data': [
        'data/l10n_uk_chart_data.xml',
        'data/account_tax_report_data.xml',
    ],
    'demo': [
        'demo/l10n_uk_demo.xml',
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
