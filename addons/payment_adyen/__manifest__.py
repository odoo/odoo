# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Adyen Payment Acquirer',
    'version': '2.0',
    'category': 'Accounting/Payment Acquirers',
    'sequence': 340,
    'summary': 'Payment Acquirer: Adyen Implementation',
    'description': """Adyen Payment Acquirer""",
    'depends': ['payment'],
    'data': [
        'views/payment_adyen_templates.xml',
        'views/payment_views.xml',
        'data/payment_acquirer_data.xml',  # Depends on views/payment_adyen_templates.xml
    ],
    'application': True,
    'uninstall_hook': 'uninstall_hook',
    'assets': {
        'web.assets_frontend': [
            'https://checkoutshopper-live.adyen.com/checkoutshopper/sdk/3.9.4/adyen.css',
            'https://checkoutshopper-live.adyen.com/checkoutshopper/sdk/3.9.4/adyen.js',
            'payment_adyen/static/src/js/payment_form.js',
        ],
    }
}
