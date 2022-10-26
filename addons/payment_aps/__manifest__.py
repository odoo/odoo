# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Payment Provider: Amazon Payment Services",
    'version': '1.0',
    'category': 'Accounting/Payment Providers',
    'sequence': 350,
    'summary': "An Amazon payment provider covering the MENA region.",
    'depends': ['payment'],
    'data': [
        'views/payment_aps_templates.xml',
        'views/payment_provider_views.xml',

        'data/payment_provider_data.xml',
    ],
    'application': True,
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
