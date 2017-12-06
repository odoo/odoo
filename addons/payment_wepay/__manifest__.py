# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'WePay Payment Acquirer',
    'category': 'Accounting',
    'summary': 'Payment Acquirer: WePay Implementation',
    'description': """WePay Payment Acquirer""",
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_wepay_template.xml',
        'data/payment_acquirer_data.xml',
    ],
}
