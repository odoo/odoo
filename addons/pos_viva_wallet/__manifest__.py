# -*- coding: utf-8 -*-
{
    'name': 'POS Viva Wallet',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 7,
    'summary': 'Integrate your POS with a Viva Wallet payment terminal',
    'data': [
        'views/pos_payment_method_views.xml',
    ],
    'depends': ['point_of_sale'],
    'installable': True,
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_viva_wallet/static/src/**/*',
        ],
        'web.assets_tests': [
            'pos_viva_wallet/static/tests/tours/**/*',
        ],
    },
    'license': 'LGPL-3',
}
