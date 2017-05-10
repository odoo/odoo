# -*- coding: utf-8 -*-

{
    'name': 'Custom Payment Acquirer',
    'category': 'Accounting',
    'summary': 'Payment Acquirer: Custom Provider',
    'version': '1.0',
    'description': """.. raw:: html

    <p>
        A generic acquirer payment provider
    </p>
    <ul>
        <li><i class="fa fa-check"/>eCommerce</li>
    </ul>
""",
    'depends': ['payment'],
    'data': [
        'views/payment_custom_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    'installable': True,
    'auto_install': True,
}
