# -*- coding: utf-8 -*-

{
    'name': 'Paypal Payment Acquirer',
    'category': 'Hidden',
    'summary': 'Payment Acquirer: Paypal Implementation',
    'version': '1.0',
    'description': """Paypal Payment Acquirer""",
    'depends': ['payment'],
    'data': [
        'views/payment_acquirer_views.xml',
        'views/payment_acquirer_templates_paypal.xml',
        'views/res_config_views.xml',
        'data/paypal_data.xml',
    ],
    'installable': True,
}
