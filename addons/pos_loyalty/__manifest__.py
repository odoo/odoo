# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Point of Sale - Coupons & Loyalty",
    'version': '2.0',
    'category': 'Sales/Point Of Sale',
    'sequence': 6,
    'summary': 'Use Coupons, Gift Cards and Loyalty programs in Point of Sale',
    'description': '',
    'depends': ['loyalty', 'point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'data/default_barcode_patterns.xml',
        'views/loyalty_card_views.xml',
        'views/loyalty_mail_views.xml',
        'views/pos_config_views.xml',
        'views/pos_loyalty_menu_views.xml',
    ],
    'demo': [
        'data/pos_loyalty_demo.xml',
    ],
    'installable': True,
    'assets': {
        'point_of_sale.assets': [
            'pos_loyalty/static/src/css/Loyalty.scss',
            'pos_loyalty/static/src/js/**/*.js',
        ],
        'web.assets_tests': [
            'pos_loyalty/static/tests/tours/**/*'
        ],
        'point_of_sale.assets_qweb': [
            'pos_loyalty/static/src/xml/**/*',
        ],
    },
    'license': 'LGPL-3',
}
