{
    'name': 'Ecuadorian eCommerce',
    'category': 'Accounting/Localizations/Website',
    'countries': ['ec'],
    'icon': '/base/static/img/country_flags/ec.png',
    'description': """Bridge Website Sale for Ecuador""",
    'depends': [
        'website_sale',
        'l10n_ec',
    ],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
