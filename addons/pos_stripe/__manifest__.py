# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'POS Stripe',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Integrate your POS with a Stripe payment terminal',
    'data': [
        'views/pos_payment_method_views.xml',
        'views/assets_stripe.xml',
    ],
    'depends': ['point_of_sale', 'payment_stripe'],
    'installable': True,
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_stripe/static/src/**/*',
        ],
        'web.assets_unit_tests': [
            'pos_stripe/static/tests/unit/data/**/*'
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
