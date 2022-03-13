# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'On site payment',
    'version': '1.0',
    'category': 'Accounting/Payment Acquirers',
    'description': """
Payment acquirer for on site payment. This allows customers to pay for their orders directly in one of
your point of sales""",
    'depends': ['point_of_sale', 'delivery', 'website_sale'],
    'data': [
        'data/payment_acquirer_data.xml',
        'data/templates.xml'
    ],
    'assets': {
        'web.assets_frontend': [
            'payment_onsite/static/src/js/website_payment_form.js'
        ],
    },
    'post_init_hook': 'create_pos_onsite_carriers',
    'application': False,
    'auto_install': True,
    'license': 'LGPL-3',
}
