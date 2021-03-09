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
        'views/pos_discount_views.xml',
        ],
    'installable': True,
    'assets': {
        'point_of_sale.assets': [
            # inside .
            'pos_discount/static/src/js/DiscountButton.js',
            # inside .
            'pos_discount/static/src/js/models.js',
        ],
        'web.assets_qweb': [
            'pos_discount/static/src/xml/DiscountButton.xml',
        ],
    }
}
