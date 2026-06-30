# -*- coding: utf-8 -*-

{
    'name': 'Website Payment',
    'category': 'Website/Website',
    'summary': 'Payment integration with website',
    'version': '1.0',
    'description': """
This is a bridge module that adds multi-website support for payment providers.
    """,
    'depends': [
        'website',
        'account_payment',
        'portal',
    ],
    'data': [
        'data/mail_templates.xml',
        'views/payment_form_templates.xml',
        'views/payment_provider.xml',
        'views/res_config_settings_views.xml',
        'views/snippets/snippets.xml',
        'views/snippets/s_donation.xml',
        'views/snippets/s_supported_payment_methods.xml',
    ],
    'auto_install': True,
    'assets': {
        'web.assets_frontend': [
            'website_payment/static/src/interactions/*',
            'website_payment/static/src/snippets/**/*.js',
            ('remove', 'website_payment/static/src/snippets/**/*.edit.js'),
        ],
        'website.assets_inside_builder_iframe': [
            'website_payment/static/src/**/*.edit.js',
        ],
        'web.assets_tests': [
            'website_payment/static/tests/tours/donation.js',
        ],
        'web.assets_unit_tests': [
            'website_payment/static/tests/builder/**/*',
        ],
        'website.website_builder_assets': [
            'website_payment/static/src/website_builder/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
