{
    'name': "France eCommerce eInvoicing",
    'version': "1.0",
    'category': 'Accounting/Localizations/Website',
    'summary': "Features for French eCommerce eInvoicing",
    'description': """
Contains features for French eCommerce eInvoicing
    """,
    'depends': ['l10n_fr', 'website_sale'],
    'data': [
        'data/data.xml',
        'views/templates.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
    'assets': {
        'web.assets_frontend': [
            # '/l10n_it_edi_website_sale/static/src/js/l10n_it_edi_website_sale.js',
        ],
        'web.assets_tests': [
            # 'l10n_it_edi_website_sale/static/tests/**/*',
        ],
    },
}
