# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Portugal - Accounting',
    'version': '1.0',
    'author': 'Odoo',
    'category': 'Accounting/Localizations/Account Charts',
    'description': 'Portugal - Accounting',
    'depends': [
        'base',
        'account',
        'base_vat',
    ],
    'data': [
        'data/account_tax_report.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
