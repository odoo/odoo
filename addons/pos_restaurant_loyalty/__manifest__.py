# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'POS - Restaurant Loyality',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Link module between pos_restaurant and pos_loyalty',
    'description': """
This module correct some behaviors when both module are installed.
""",
    'depends': ['pos_restaurant', 'pos_loyalty'],
    'installable': True,
    'auto_install': True,
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_restaurant_loyalty/static/src/**/*',
        ],
        'web.assets_tests': [
            'pos_restaurant_loyalty/static/tests/tours/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
