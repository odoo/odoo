# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'POS Restaurant Adyen',
    'version': '1.0',
    'category': 'Point of Sale',
    'sequence': 6,
    'summary': 'Adds American style tipping to Adyen',
    'description': '',
    'depends': ['pos_adyen', 'pos_restaurant', 'payment_adyen'],
    'data': [
        'views/pos_payment_method_views.xml',
        'views/point_of_sale_assets.xml',
    ],
    'auto-install': True,
    'license': 'LGPL-3',
}
