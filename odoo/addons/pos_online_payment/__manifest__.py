# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Point of Sale online payment',
    'depends': ['point_of_sale', 'account_payment'],
    'data': [
        'views/payment_transaction_views.xml',
        'views/pos_payment_views.xml',
        'views/pos_payment_method_views.xml',
        'views/payment_portal_templates.xml',
        'views/account_payment_views.xml',
    ],
    'auto_install': True,
    'installable': True,
    'assets': {
        'point_of_sale.assets_prod': [
            'pos_online_payment/static/src/app/**/*',
            'pos_online_payment/static/src/css/**/*',
        ],
        'web.assets_tests': [
            'pos_online_payment/static/tests/tours/**/*',
        ],
    },
    'license': 'LGPL-3',
}
