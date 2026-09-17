{
    'name': 'Spain - ECommerce',
    'depends': ['l10n_es', 'website_sale'],
    'data': [
        'views/res_config_settings_views.xml',
        'views/address_form_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'l10n_es_website_sale/static/src/interactions/l10n_es_id_type.js',
        ],
    },
    'category': 'Accounting/Localizations/Website',
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
