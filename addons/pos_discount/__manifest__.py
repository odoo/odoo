# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Point of Sale Discounts',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Simple Discounts in the Point of Sale ',
    'description': """

This module allows the cashier to quickly give percentage-based
discount to a customer.

""",
    'depends': ['point_of_sale'],
    'data': [
        'data/pos_discount_data.xml',
        'views/res_config_settings_views.xml',
        'views/pos_config_views.xml',
        'views/pos_session_sales_details.xml',
        ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_discount/static/src/**/*',
        ],
        'web.assets_tests': [
            'pos_discount/static/tests/tours/**/*',
        ],
        'web.assets_unit_tests': [
            'pos_discount/static/tests/unit/**/*'
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
