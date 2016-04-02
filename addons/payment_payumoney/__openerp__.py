# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'PayuMoney Payment Acquirer',
    'category': 'Payment Acquirer',
    'summary': 'Payment Acquirer: PayuMoney Implementation',
    'description': """
    PayuMoney Payment Acquirer for India.

    PayUmoney payment gateway supports only INR currency.
    """,
    'depends': ['payment'],
    'data': [
        'views/payumoney.xml',
        'views/payment_acquirer.xml',
        'data/payment_payumoney_data.xml',
    ],
    'license': 'OEEL-1',
}
