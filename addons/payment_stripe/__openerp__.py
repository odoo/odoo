# -*- coding: utf-8 -*-

{
    'name': 'Stripe Payment Acquirer',
    'category': 'Hidden',
    'summary': 'Payment Acquirer: Stripe Implementation',
    'version': '1.0',
    'description': """Stripe Payment Acquirer""",
    'depends': ['payment'],
    'data': [
        'views/stripe.xml',
        'views/payment_acquirer.xml',
        'views/payment_stripe_template.xml',
        'data/payment_stripe_data.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'license': 'OEEL-1',
}
