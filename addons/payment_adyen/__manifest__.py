# -*- coding: utf-8 -*-

{
    'name': 'Adyen Payment Acquirer',
    'category': 'Accounting',
    'summary': 'Payment Acquirer: Adyen Implementation',
    'version': '1.0',
    'description': """.. raw:: html

    <p>
        A payment gateway to accept online payments via credit cards, debit cards and bank transfers.
    </p>
    <ul>
        <li><i class="fa fa-check"/>eCommerce</li>
    </ul>
""",
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_adyen_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    'installable': True,
}
