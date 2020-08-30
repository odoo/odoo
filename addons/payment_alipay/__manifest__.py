# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Alipay Payment Acquirer',
    'category': 'Accounting/Payment Acquirers',
    'sequence': 345,
    'summary': 'Payment Acquirer: Alipay Implementation',
    'description': """Alipay Payment Acquirer""",
    'depends': ['payment'],
    'data': [
        'views/alipay_views.xml',
        'views/payment_alipay_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    'application': True,
    'post_init_hook': 'create_missing_journal_for_acquirers',
}
