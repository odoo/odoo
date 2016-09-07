# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'PayuMoney Payment Acquirer',
    'category': 'Payment Acquirer',
    'summary': 'Payment Acquirer: PayuMoney Implementation',
    'description': """.. raw:: html

    <p>
        PayU India is an online payments solutions company serving the Indian market.
    </p>
    <ul class="list-inline">
        <li><i class="fa fa-check"/>eCommerce</li>
        <li><i class="fa fa-check"/>Subscription</li>
        <li><i class="fa fa-check"/>Pay button in emails</li>
    </ul>
""",
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_payumoney_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
}
