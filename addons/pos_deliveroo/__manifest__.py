# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Deliveroo Integration Point of Sale',
    'category': 'Sales/Point of Sale',
    'depends': ['point_of_sale'],
    'license': 'LGPL-3',
    'data': [
        'views/pos_delivery_service.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_deliveroo/static/src/**/*',
        ],
        'web.assets_tests': [
            'pos_deliveroo/static/tests/**/*',
        ],
    },
}
