# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Adyen Payment Acquirer',
    'category': 'Accounting/Payment Acquirers',
    'sequence': 340,
    'summary': 'Payment Acquirer: Adyen Implementation',
    'version': '1.0',
    'description': """Adyen Payment Acquirer""",
    'depends': ['payment'],
    'data': [
        'views/payment_adyen_templates.xml',
        'views/payment_views.xml',
        'views/assets.xml',
        'data/payment_acquirer_data.xml',  # Depends on views/payment_adyen_templates.xml
    ],
    'installable': True,
    'application': True,
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
}
