{
    'name': 'Spain - Modelo 130 Tax report',
    'website': 'https://www.odoo.com/documentation/18.0/applications/finance/fiscal_localizations/spain.html',
    'version': '1.0',
    'icon': '/account/static/description/l10n.png',
    'countries': ['es'],
    'category': 'Accounting/Localizations/Account Charts',
    'depends': [
        'l10n_es',
    ],
    'data': [
        'data/mod130.xml',
    ],
    'post_init_hook': '_add_mod130_tax_tags',
    'license': 'LGPL-3',
}
