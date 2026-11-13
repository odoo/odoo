# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Point of Sale - Restaurant Deposit',
    'category': 'Sales/Point Of Sale',
    'summary': 'Handle deposits in Restaurant POS',
    'description': """
This module adds deposit support to the Restaurant Point of Sale, including course handling, combo products, and bill splitting.
""",
    'depends': [
        'pos_restaurant',
        'pos_deposit',
    ],
    'auto_install': True,
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_restaurant_deposit/static/src/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
