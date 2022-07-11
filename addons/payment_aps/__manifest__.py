# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Payment Acquirer: Amazon Payment Services",
    'version': '1.0',
    'category': 'Accounting/Payment Acquirers',
    'sequence': 347,
    'summary': "Amazon Payment Services' online payment provider covering the MENA region.",
    'depends': ['payment'],
    'data': [
        'views/payment_aps_templates.xml',
        'views/payment_views.xml',

        'data/payment_acquirer_data.xml',
    ],
    'application': True,
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
