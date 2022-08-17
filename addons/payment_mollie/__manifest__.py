# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Mollie Payment Provider',
    'version': '1.0',
    'category': 'Accounting/Payment Providers',
    'sequence': 365,
    'summary': 'Payment Provider: Mollie Implementation',
    'description': """Mollie Payment Provider""",
    'author': 'Odoo S.A, Applix BV, Droggol Infotech Pvt. Ltd.',
    'website': 'https://www.mollie.com',

    'depends': ['payment'],
    'data': [
        'views/payment_mollie_templates.xml',
        'views/payment_views.xml',
        'data/payment_provider_data.xml',
    ],
    'application': True,
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3'
}
