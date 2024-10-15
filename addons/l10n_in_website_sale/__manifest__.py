{
    'name': 'Indian eCommerce',
    'description': 'Indian Localization E-Commerce Module',
    'version': '1.0',
    'depends': ['l10n_in', 'website_sale'],
    'auto_install': True,
    'installable': True,
    'license': 'LGPL-3',
    'data': [
        'views/templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'l10n_in_website_sale/static/src/js/address.js',
            'l10n_in_website_sale/static/src/js/portal.js',
        ]
    }
}
