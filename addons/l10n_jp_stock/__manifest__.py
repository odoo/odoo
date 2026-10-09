# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Japan - Stock Document Layout',
    'countries': ['jp'],
    'category': 'Accounting/Localizations',
    'author': 'Odoo S.A.',
    'depends': [
        'l10n_jp',
        'stock',
    ],
    'data': [
        'report/report_deliveryslip.xml',
        'report/report_return_slip.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
