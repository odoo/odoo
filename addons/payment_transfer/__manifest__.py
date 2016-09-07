# -*- coding: utf-8 -*-

{
    'name': 'Transfer Payment Acquirer',
    'category': 'Accounting',
    'summary': 'Payment Acquirer: Transfer Implementation',
    'version': '1.0',
    'description': """.. raw:: html

    <p>
        Provide instructions to customers so that they can pay their orders manually.
    </p>
    <ul>
        <li><i class="fa fa-check"/>eCommerce</li>
    </ul>
""",
    'depends': ['payment'],
    'data': [
        'views/payment_transfer_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    'installable': True,
    'auto_install': True,
}
