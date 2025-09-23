# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'POS Self-Order / Online Payment',
    'category': 'Sales/Point of Sale',
    'summary': 'Support online payment in self-order',
    'version': '1.0',
    'depends': ['pos_online_payment', 'pos_self_order'],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'assets': {
        'pos_self_order.assets': [
            'pos_online_payment_self_order/static/src/app/**/*',
            'point_of_sale/static/lib/qrcode.js',
        ],
        'point_of_sale._assets_pos': [
            'pos_online_payment_self_order/static/src/overrides/**/*',
        ],
        'web.assets_tests': [
            'pos_online_payment_self_order/static/tests/tours/pos_online_payment_multi_table_order.js',
        ],
        'pos_self_order.assets_tests': [
            'pos_online_payment_self_order/static/tests/tours/pos_self_order_mobile_online_payment_tour.js',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
