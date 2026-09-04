{
    'name': 'Odoo Enterprise Theme',
    'version': '16.0.1.0.1',
    'summary': 'Odoo Enterprise Theme',
    'author': 'Bytelegion',
    'license': 'AGPL-3',
    'maintainer': 'Bytelegion',
    'company': 'Bytelegion',
    'website': 'https://bytelegions.com',
    'depends': [
        'web'
    ],
    'category':'Branding',
    'description': """
           Odoo Enterprise Theme
    """,
    'assets': {
        'web._assets_primary_variables': [
            '/legion_enterprise_theme/static/src/scss/primary_variables_custom.scss',
        ],
        'web.assets_common': [
            '/legion_enterprise_theme/static/src/scss/fields_extra_custom.scss',
        ],
        'web._assets_secondary_variables': [
            '/legion_enterprise_theme/static/src/scss/secondary_variables.scss',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
    'images': ['static/description/banner.gif'], 
    
}
