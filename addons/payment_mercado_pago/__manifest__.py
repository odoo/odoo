# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Payment Acquirer: Mercado Pago",
    'version': '1.0',
    'category': 'Accounting/Payment Acquirers',
    'sequence': 350,
    'summary': "An online payments provider covering several countries, currencies and payment "
               "methods from Latin America.",
    'depends': ['payment'],
    'data': [
        'views/payment_mercado_pago_templates.xml',
        'views/payment_views.xml',

        'data/payment_acquirer_data.xml',  # Depends on views/payment_mercado_pago_templates.xml
    ],
    'application': True,
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
