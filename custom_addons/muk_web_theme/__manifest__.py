{
    'name': 'MuK Backend Theme', 
    'summary': 'Odoo Community Backend Theme',
    'description': '''
        This module offers a mobile compatible design for Odoo Community. 
        Furthermore it allows the user to define some design preferences.
    ''',
    'version': '17.0.1.2.1',
    'category': 'Themes/Backend', 
    'license': 'LGPL-3', 
    'author': 'MuK IT',
    'website': 'http://www.mukit.at',
    'live_test_url': 'https://mukit.at/demo',
    'contributors': [
        'Mathias Markl <mathias.markl@mukit.at>',
    ],
    'depends': [
        'muk_web_chatter',
        'muk_web_dialog',
        'muk_web_appsbar',
        'muk_web_colors',
    ],
    'excludes': [
        'web_enterprise',
    ],
    'data': [
        'templates/web_layout.xml',
        'views/res_config_settings.xml',
    ],
    'assets': {
        'web._assets_primary_variables': [
            (
                'after', 
                'web/static/src/scss/primary_variables.scss', 
                'muk_web_theme/static/src/scss/colors.scss'
            ),
            (
                'after', 
                'web/static/src/scss/primary_variables.scss', 
                'muk_web_theme/static/src/scss/variables.scss'
            ),
        ],
        'web.assets_backend': [
            'muk_web_theme/static/src/webclient/**/*.xml',
            'muk_web_theme/static/src/webclient/**/*.scss',
            'muk_web_theme/static/src/webclient/**/*.js',
            'muk_web_theme/static/src/views/**/*.scss',
        ],
    },
    'images': [
        'static/description/banner.png',
        'static/description/theme_screenshot.png'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'post_init_hook': '_setup_module',
    'uninstall_hook': '_uninstall_cleanup',
}
