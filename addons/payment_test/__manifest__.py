# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Test Payment Acquirer',
    'category': 'Tools',
    'description': """
This module implements a simple test payment acquirer flow to allow
the testing of successful payments behaviors on the e-commerce.

It also prevents its usage for production environment to avoid any potential misuse.
""",
    'version': '1.0',
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'data/payment_acquirer_data.xml',
    ],
    'installable': True,
    'post_init_hook': 'create_missing_journal_for_acquirers',
}
