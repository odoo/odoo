# -*- coding: utf-8 -*-

{
    'name': 'Transfer Payment Acquirer',
    'category': 'Accounting/Payment Acquirers',
    'summary': 'Payment Acquirer: Transfer Implementation',
    'version': '1.0',
    'description': """Transfer Payment Acquirer""",
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_transfer_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    'installable': True,
    'auto_install': True,
    'post_init_hook': 'create_missing_journal_for_acquirers',
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
