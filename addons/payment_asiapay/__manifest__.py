# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Payment Acquirer: AsiaPay",
    'version': '1.0',
    'category': 'Accounting/Payment Acquirers',
    'sequence': 350,
    'summary': "An online payments provider based in Hong Kong covering most Asian countries and "
               "many different payment methods.",
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_asiapay_templates.xml',

        'data/payment_acquirer_data.xml',
    ],
    'application': True,
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
