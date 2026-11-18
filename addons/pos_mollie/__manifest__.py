# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'POS Mollie',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Integrate your POS with a Mollie payment terminal',
    'description': """
Mollie terminal payments
=========================

This module enables customers to conveniently pay POS orders by utilizing the Mollie terminal and making payments through various cards.
    """,

    'author': 'Odoo S.A., Applix BV, Droggol Infotech Pvt. Ltd.',
    'license': 'LGPL-3',
    'depends': ['point_of_sale'],
    'installable': True,
    'data': [
        'views/pos_payment_method_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_mollie/static/**/*',
        ],
    },
}
