# -*- coding: utf-8 -*-

{
    'name': 'Ogone Payment Acquirer',
    'category': 'Accounting',
    'summary': 'Payment Acquirer: Ogone Implementation',
    'version': '1.0',
    'description': """Ogone Payment Acquirer""",
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_ogone_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    'installable': True,
    'post_init_hook': 'create_missing_journal_for_acquirers',
    'uninstall_hook': 'uninstall_hook',
}
