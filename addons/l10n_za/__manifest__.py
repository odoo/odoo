# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'South Africa - Accounting',
    'version': '1.0',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This is the latest basic South African localisation necessary to run Odoo in ZA:
================================================================================
    - a generic chart of accounts
    - SARS VAT Ready Structure""",
    'author': 'Paradigm Digital',
    'website': 'https://www.paradigmdigital.co.za',
    'depends': [
        'account',
        'base_vat',
    ],
    'data': [
        'data/account.account.tag.csv',
        'data/account_tax_report_data.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
