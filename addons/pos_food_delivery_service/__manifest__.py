# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Food Delivery Service',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Integratation of food delivery services with your Point of Sale',
    'depends': ['pos_restaurant'],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_online_delivery_provider.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_food_delivery_service/static/src/**/*',
        ],
        'web.assets_tests': [
            'pos_food_delivery_service/static/tests/tours/**/*',
        ],
    },
    'license': 'LGPL-3',
}
