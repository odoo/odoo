# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Stripe Payment Acquirer',
    'version': '2.0',
    'category': 'Accounting/Payment Acquirers',
    'sequence': 380,
    'summary': 'Payment Acquirer: Stripe Implementation',
    'description': """Stripe Payment Acquirer""",
    'depends': ['payment'],
    'data': [
        'views/assets.xml',
        'views/payment_views.xml',
        'data/payment_acquirer_data.xml',
    ],
    'application': True,
    'post_init_hook': 'create_missing_journals',
    'uninstall_hook': 'uninstall_hook',
}
