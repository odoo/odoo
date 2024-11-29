# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Payment Provider: Mercado Pago",
    'version': '1.0',
    'category': 'Accounting/Payment Providers',
    'sequence': 350,
    'summary': "A payment provider covering several countries in Latin America.",
    'description': " ",  # Non-empty string to avoid loading the README file.
    'depends': ['payment'],
    'data': [
        'views/payment_form_templates.xml',
        'views/payment_mercado_pago_templates.xml',
        'views/payment_provider_views.xml',

        'data/payment_provider_data.xml',  # Depends on views/payment_mercado_pago_templates.xml
    ],
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'assets': {
        'web.assets_frontend': [
            'payment_mercado_pago/static/src/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
