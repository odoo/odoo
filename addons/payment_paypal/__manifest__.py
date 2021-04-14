# -*- coding: utf-8 -*-

{
    'installable': False,
    'name': 'Paypal Payment Acquirer',
    'category': 'Accounting/Payment Acquirers',
    'sequence': 365,
    'summary': 'Payment Acquirer: Paypal Implementation',
    'version': '1.0',
    'description': """Paypal Payment Acquirer""",
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_paypal_templates.xml',
        'data/payment_acquirer_data.xml',
        'data/payment_paypal_email_data.xml',
    ],
    'application': True,
    'post_init_hook': 'create_missing_journal_for_acquirers',
    'uninstall_hook': 'uninstall_hook',
}
