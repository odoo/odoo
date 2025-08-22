{
    'name': 'Argentinean eCommerce',
    'version': '1.0',
    'category': 'Accounting/Localizations/Website',
    'countries': ['ar'],
    'icon': '/base/static/img/country_flags/ar.png',
    'description': """Bridge Website Sale for Argentina""",
    'depends': [
        'website_sale',
        'l10n_ar',
    ],
    'data': [
        'views/res_config_settings_views.xml',
        'views/templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'l10n_ar_website_sale/static/src/interactions/**/*',
            'l10n_ar_website_sale/static/src/scss/*.scss',
        ]
    },
    'installable': True,
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
