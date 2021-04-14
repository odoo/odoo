# -*- coding: utf-8 -*-

{
    'installable': False,
    'name': 'Ingenico Payment Acquirer',
    'category': 'Accounting/Payment Acquirers',
    'sequence': 360,
    'summary': 'Payment Acquirer: Ingenico Implementation',
    'version': '1.0',
    'description': """Ingenico Payment Acquirer""",
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_ingenico_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    'application': True,
    'post_init_hook': 'create_missing_journal_for_acquirers',
    'uninstall_hook': 'uninstall_hook',
}
