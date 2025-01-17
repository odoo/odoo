# -*- coding: utf-8 -*-

{
    'name': 'Website Payment',
    'category': 'Hidden',
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
    ],
    'auto_install': True,
    'assets': {
        'website.assets_wysiwyg': [
            'website_payment/static/src/snippets/s_donation/options.js',
            'website_payment/static/src/snippets/s_donation/options.xml',
        ],
        'web.assets_frontend': [
            'website_payment/static/src/js/*',
            'website_payment/static/src/interactions/*',
            'website_payment/static/src/snippets/**/*.js',
            ('remove', 'website_payment/static/src/snippets/**/*.edit.js'),
            ('remove', 'website_payment/static/src/snippets/**/options.js'),
        ],
        'website.assets_edit_frontend': [
            'website_payment/static/src/**/*.edit.js',
        ],
        'web.assets_tests': [
            'website_payment/static/tests/tours/donation.js',
        ],
    },
    'license': 'LGPL-3',
}
