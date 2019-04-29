# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Test Payment Acquirer',
    'version': '1.0',
    'category': 'Hidden',
    'description': """
This module implements a simple test payment acquirer flow to allow
the testing of successful payments behaviors on e-commerce. It includes
a protection to avoid using it in production environment. However, do
not use it in production environment.
""",
    'depends': ['payment'],
    'data': [
        'views/payment_test_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    'installable': True,
    'post_init_hook': 'create_missing_journal_for_acquirers',
}
