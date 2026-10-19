
{
    'name': 'Website Payment',
    'category': 'Website/Website',
    'summary': 'Payment integration with website',
    'description': """
This is a bridge module that adds multi-website support for payment providers.
    """,
    'depends': [
        'website',
        'account_payment',
        'portal',
    ],
    'data': [
        'views/payment_provider.xml',
        'views/res_config_settings_views.xml',
        'views/snippets/snippets.xml',
        'views/snippets/s_supported_payment_methods.xml',
    ],
    'auto_install': True,
    'assets': {
        'web.assets_frontend': [
            'website_payment/static/src/snippets/**/*.js',
            ('remove', 'website_payment/static/src/snippets/**/*.edit.js'),
        ],
        'website.assets_inside_builder_iframe': [
            'website_payment/static/src/**/*.edit.js',
        ],
        'website.website_builder_assets': [
            'website_payment/static/src/website_builder/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
