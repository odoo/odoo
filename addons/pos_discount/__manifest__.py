# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Point of Sale Discounts',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Simple Discounts in the Point of Sale ',
    'description': """

This module allows the cashier to quickly give percentage-based
discount to a customer.

""",
    'depends': ['point_of_sale'],
    'data': [
        'views/res_config_settings_views.xml',
        'views/pos_config_views.xml',
        ],
    'installable': True,
    'assets': {
        'point_of_sale.assets': [
            'pos_discount/static/src/js/**/*',
            'pos_discount/static/src/xml/**/*',
        ],
    },
    'license': 'LGPL-3',
}
