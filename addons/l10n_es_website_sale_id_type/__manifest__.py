{
    'name': 'Spain - eCommerce ID Types',
    'summary': "Let customers pick the type of their identification document at checkout",
    'category': 'Accounting/Localizations/Website',
    'depends': ['l10n_es_website_sale'],
    'auto_install': True,
    'data': [
        'views/address_form_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'l10n_es_website_sale_id_type/static/src/interactions/l10n_es_id_type.js',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
