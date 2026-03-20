# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Colombian - Point of Sale',
    'description': """Colombian - Point of Sale""",
    'category': 'Accounting/Localizations/Point of Sale',
    'auto_install': True,
    'data': [
        'receipt/pos_order_receipt.xml',
    ],
    'depends': [
        'l10n_co',
        'point_of_sale'
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_co_pos/static/src/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
