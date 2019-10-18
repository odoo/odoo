# -*- coding: utf-8 -*-

{
    'name': 'Ingenico Payment Acquirer',
    'category': 'Accounting/Payment',
    'summary': 'Payment Acquirer: Ingenico Implementation',
    'version': '1.0',
    'description': """Ingenico Payment Acquirer""",
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_ingenico_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    'installable': True,
    'post_init_hook': 'create_missing_journal_for_acquirers',
}
