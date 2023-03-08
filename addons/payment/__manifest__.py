# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Payment Engine",
    'version': '2.0',
    'category': 'Hidden',
    'summary': "The payment engine used by payment provider modules.",
    'depends': ['portal'],
    'data': [
        'data/payment_method_data.xml',
        'data/payment_provider_data.xml',
        'data/payment_cron.xml',

        'views/payment_portal_templates.xml',
        'views/payment_templates.xml',

        'views/payment_provider_views.xml',
        'views/payment_method_views.xml',
        'views/payment_transaction_views.xml',
        'views/payment_token_views.xml',  # Depends on `action_payment_transaction_linked_to_token`
        'views/res_partner_views.xml',

        'security/ir.model.access.csv',
        'security/payment_security.xml',

        'wizards/payment_capture_wizard_views.xml',
        'wizards/payment_link_wizard_views.xml',
        'wizards/payment_onboarding_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'payment/static/src/scss/portal_payment.scss',
            'payment/static/src/scss/payment_templates.scss',
            'payment/static/src/scss/payment_form.scss',
            'payment/static/lib/jquery.payment/jquery.payment.js',
            'payment/static/src/js/checkout_form.js',
            'payment/static/src/js/express_checkout_form.js',
            'payment/static/src/js/manage_form.js',
            'payment/static/src/js/payment_form_mixin.js',
            'payment/static/src/js/post_processing.js',
            'payment/static/src/xml/payment_post_processing.xml',
        ],
        'web.assets_backend': [
            'payment/static/src/scss/payment_provider.scss',
        ],
    },
    'license': 'LGPL-3',
}
