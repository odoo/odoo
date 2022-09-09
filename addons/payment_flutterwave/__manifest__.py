# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Payment Provider: Flutterwave",
    'version': '1.0',
    'category': 'Accounting/Payment Providers',
    'sequence': 360,
    'summary': "A Nigerian online payments provider covering several African countries and payment "
               "methods.",
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_flutterwave_templates.xml',

        'data/payment_provider_data.xml',
    ],
    'application': True,
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
