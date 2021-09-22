# -*- coding: utf-8 -*-

{
    'name': 'Website Payment',
    'category': 'Hidden',
    'summary': 'Payment integration with website',
    'version': '1.0',
    'description': """
This is a bridge module that adds multi-website support for payment acquirers.
    """,
    'depends': [
        'website',
        'payment',
        'portal',
    ],
    'data': [
        'data/donation_data.xml',
        'views/payment_acquirer.xml',
        'views/donation_templates.xml',
        'views/snippets/snippets.xml',
        'views/snippets/s_donation.xml',
    ],
    'auto_install': True,
    'assets': {
        'website.assets_wysiwyg': [
            'website_payment/static/src/snippets/s_donation/options.js',
        ],
        'web.assets_frontend': [
            'website_payment/static/src/js/website_payment_donation.js',
            'website_payment/static/src/js/website_payment_form.js',
        ],
    },
    'license': 'LGPL-3',
}
