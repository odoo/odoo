# -*- coding: utf-8 -*-

{
    'name': 'Paypal Payment Acquirer',
    'category': 'Accounting',
    'summary': 'Payment Acquirer: Paypal Implementation',
    'version': '1.0',
    'description': """.. raw:: html

    <p>
        A payment gateway to accept online payments via credit cards and e-checks.
    </p>
    <ul class="list-inline">
        <li><i class="fa fa-check"/>eCommerce</li>
        <li><i class="fa fa-check"/>Cards storage</li>
        <li><i class="fa fa-check"/>Authorize &amp; Capture</li>
    </ul>
""",
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_paypal_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    'installable': True,
}
