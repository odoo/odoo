# -*- coding: utf-8 -*-

{
    'name': 'Authorize.Net Payment Acquirer',
    'category': 'Accounting',
    'summary': 'Payment Acquirer: Authorize.net Implementation',
    'version': '1.0',
    'description': """Authorize.Net Payment Acquirer""",
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_authorize_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    'installable': True,
    'post_init_hook': 'create_missing_journal_for_acquirers',
}
