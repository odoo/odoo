# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'POS PayTM',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Integrate your POS with a PayTM payment terminal',
    'description': '',
    'data': [
        'views/pos_payment_method_views.xml',
    ],
    'depends': ['point_of_sale', 'payment_paytm'],
    'installable': True,
    'assets': {
        'point_of_sale.assets': [
            'pos_paytm/static/**/*',
        ],
    },
    'license': 'LGPL-3',
}
