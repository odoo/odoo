# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Test Payment Acquirer',
    'version': '2.0',
    'category': 'Hidden',
    'description': " ",  # Non-empty string to avoid loading the README file.
    'depends': ['payment'],
    'data': [
        'views/payment_templates.xml',
        'views/payment_test_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    'uninstall_hook': 'uninstall_hook',
    'assets': {
        'web.assets_frontend': [
            'payment_test/static/src/js/**/*',
        ],
    },
    'license': 'LGPL-3',
}
