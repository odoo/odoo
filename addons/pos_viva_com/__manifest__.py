# -*- coding: utf-8 -*-
{
    'name': 'PoS Viva.com',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 7,
    'summary': 'Integrate your PoS with a Viva.com payment terminal',
    'data': [
        'views/pos_payment_method_views.xml',
    ],
    'depends': ['point_of_sale'],
    'installable': True,
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_viva_com/static/src/**/*',
        ],
        'web.assets_tests': [
            'pos_viva_com/static/tests/tours/**/*',
        ],
        'web.assets_unit_tests': [
            'pos_viva_com/static/tests/unit/data/**/*'
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
