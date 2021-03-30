# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'PayuMoney Payment Acquirer',
    'version': '2.0',
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
    'post_init_hook': 'create_missing_journals',
    'uninstall_hook': 'uninstall_hook',
}
