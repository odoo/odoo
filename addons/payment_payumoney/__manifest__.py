# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'PayuMoney Payment Acquirer',
    'category': 'Accounting/Payment Acquirers',
    'sequence': 375,
    'summary': 'Payment Acquirer: PayuMoney Implementation',
    'description': """
    PayuMoney Payment Acquirer for India.

    PayUmoney payment gateway supports only INR currency.
    """,
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_payumoney_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    'application': True,
    'post_init_hook': 'create_missing_journal_for_acquirers',
    'uninstall_hook': 'uninstall_hook',
}
