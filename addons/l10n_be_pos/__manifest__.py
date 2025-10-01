# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'l10n_be_pos',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Link module between point_of_sale and l10n_be',
    'depends': ['point_of_sale', 'l10n_be', 'account'],
    'auto_install': True,
    'data': [
        'data/default_cash_rounding.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
