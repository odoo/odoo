# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Razorpay Payment Acquirer',
    'category': 'Accounting',
    'summary': 'Payment Acquirer: Razorpay Implementation',
    'version': '1.0',
    'description': """Razorpay Payment Acquirer""",
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_razorpay_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    'post_init_hook': 'create_missing_journal_for_acquirers',
}
