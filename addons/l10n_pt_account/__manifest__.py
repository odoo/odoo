# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Portugal - Accounting',
    'version': '1.0',
    'author': 'Odoo',
    'icon': '/account/static/description/l10n.png',
    'countries': ['pt'],
    'category': 'Accounting/Localizations/Account Charts',
    'description': 'Portugal - Accounting',
    'depends': [
        'base',
        'account',
        'base_vat',
        'l10n_pt',
    ],
    'auto_install': [
        'account',
        'l10n_pt',
    ],
    'data': [
        'data/account_tax_report.xml',
        'data/ir_cron.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
