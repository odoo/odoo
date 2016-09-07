# -*- coding: utf-8 -*-

{
    'name': 'Stripe Payment Acquirer',
    'category': 'Hidden',
    'summary': 'Payment Acquirer: Stripe Implementation',
    'version': '1.0',
    'description': """.. raw:: html

    <p>
        A payment gateway to accept online payments via credit cards.
    </p>
    <ul>
        <li><i class="fa fa-check"/>eCommerce</li>
    </ul>
""",
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_stripe_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
}
