# -*- coding: utf-8 -*-

{
    'installable': False,
    'name': 'Adyen Payment Acquirer',
    'category': 'Accounting/Payment Acquirers',
    'sequence': 340,
    'summary': 'Payment Acquirer: Adyen Implementation',
    'version': '1.0',
    'description': """Adyen Payment Acquirer""",
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_adyen_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    'application': True,
    'post_init_hook': 'create_missing_journal_for_acquirers',
    'uninstall_hook': 'uninstall_hook',
}
