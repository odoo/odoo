# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Payment Provider: Adyen',
    'version': '2.0',
    'category': 'Accounting/Payment Providers',
    'sequence': 350,
    'summary': "A Dutch payment provider covering Europe and the US.",
    'depends': ['payment'],
    'data': [
        'views/payment_adyen_templates.xml',
        'views/payment_form_templates.xml',
        'views/payment_provider_views.xml',

        'data/payment_provider_data.xml',  # Depends on views/payment_adyen_templates.xml

        'wizards/payment_capture_wizard_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'assets': {
        'web.assets_frontend': [
            'payment_adyen/static/src/js/payment_form.js',
        ],
    },
    'license': 'LGPL-3',
}
