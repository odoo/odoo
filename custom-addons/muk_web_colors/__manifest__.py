{
    'name': 'MuK Colors', 
    'summary': 'Customize your Odoo colors',
    'description': '''
        This module gives you options to customize the theme colors.
    ''',
    'version': '19.0.1.0.0',
    'category': 'Tools/UI',
    'license': 'LGPL-3', 
    'author': 'MuK IT',
    'website': 'http://www.mukit.at',
    'live_test_url': 'https://youtu.be/yNKoA8768m8',
    'contributors': [
        'Mathias Markl <mathias.markl@mukit.at>',
    ],
    'depends': [
        'web',
        'base_setup',
    ],
    'data': [
        'templates/webclient.xml',
        'views/res_config_settings.xml',
    ],
    'assets': {
        'web._assets_primary_variables': [
            ('prepend', 'muk_web_colors/static/src/scss/colors.scss'),
            (
                'before', 
                'muk_web_colors/static/src/scss/colors.scss', 
                'muk_web_colors/static/src/scss/colors_light.scss'
            ),
        ],
        'web.assets_web_dark': [
            (
                'after', 
                'muk_web_colors/static/src/scss/colors.scss', 
                'muk_web_colors/static/src/scss/colors_dark.scss'
            ),
        ],
    },
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'uninstall_hook': '_uninstall_cleanup',
}
