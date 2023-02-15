# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Payment Provider: Flutterwave",
    'version': '1.0',
    'category': 'Accounting/Payment Providers',
    'sequence': 350,
    'summary': "A Nigerian payment provider covering several African countries.",
    'depends': ['payment'],
    'data': [
        'views/payment_flutterwave_templates.xml',
        'views/payment_provider_views.xml',

        'data/payment_provider_data.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
