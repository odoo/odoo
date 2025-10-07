{
    'name': 'Odoo Enterprise Theme',
    'version': '16.0.0.3',
    'summary': 'Odoo Enterprise Theme',
    'author': 'fl1 sro',
    'license': 'AGPL-3',
    'maintainer': 'Fl1',
    'company': 'Fl1 sro',
    'website': 'https://fl1.cz',
    'depends': [
        'web'
    ],
    'category':'Branding',
    'description': """
           Odoo Enterprise Theme
    """,
    'assets': {
        'web._assets_primary_variables': [
            '/enterprise_theme_mod/static/src/scss/primary_variables_custom.scss',
        ],
        'web.assets_common': [
            '/enterprise_theme_mod/static/src/scss/fields_extra_custom.scss',
        ],
        'web._assets_secondary_variables': [
            '/enterprise_theme_mod/static/src/scss/secondary_variables.scss',
        ],
    },
    'price':0,
    'currency':'EUR',
    'installable': True,
    'auto_install': False,
    'application': True,
    'images': ['static/description/icon.png']
}
