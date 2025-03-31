# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Payment Engine",
    'version': '2.0',
    'category': 'Hidden',
    'summary': "The payment engine used by payment provider modules.",
    'depends': ['onboarding', 'portal'],
    'data': [
        # Record data.
        'data/ir_actions_server_data.xml',
        'data/onboarding_data.xml',
        'data/payment_method_data.xml',
        'data/payment_provider_data.xml',
        'data/payment_cron.xml',

        # QWeb templates.
        'views/express_checkout_templates.xml',
        'views/payment_form_templates.xml',
        'views/portal_templates.xml',

        # Model views.
        'views/payment_provider_views.xml',
        'views/payment_method_views.xml',  # Depends on `action_payment_provider`.
        'views/payment_transaction_views.xml',
        'views/payment_token_views.xml',  # Depends on `action_payment_transaction_linked_to_token`.
        'views/res_partner_views.xml',

        # Security.
        'security/ir.model.access.csv',
        'security/payment_security.xml',

        # Wizard views.
        'wizards/payment_capture_wizard_views.xml',
        'wizards/payment_link_wizard_views.xml',
        'wizards/payment_onboarding_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'payment/static/lib/jquery.payment/jquery.payment.js',
            'payment/static/src/**/*',
            ('remove', 'payment/static/src/js/payment_wizard_copy_clipboard_field.js'),
        ],
        'web.assets_backend': [
            'payment/static/src/scss/payment_provider.scss',
            'payment/static/src/js/payment_wizard_copy_clipboard_field.js',
        ],
        'web.qunit_suite_tests': [
            'payment/static/tests/payment_wizard_copy_clipboard_field_tests.js',
        ],
    },
    'license': 'LGPL-3',
}
