# -*- coding: utf-8 -*-

{
    'name': 'Ogone Payment Acquirer',
    'category': 'Accounting',
    'summary': 'Payment Acquirer: Ogone Implementation',
    'version': '1.0',
    'description': """.. raw:: html

    <p>
        Ingenico Payment Services (formerly Ogone) supports credit cards, debit cards and bank transfers.
    </p>
    <ul class="list-inline">
        <li><i class="fa fa-check"/>eCommerce</li>
        <li><i class="fa fa-check"/>Cards storage</li>
        <li><i class="fa fa-check"/>Pay button in emails</li>
    </ul>
""",
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_ogone_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    'installable': True,
}
