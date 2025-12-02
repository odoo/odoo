{
    'name': 'MuK AppsBar', 
    'summary': 'Adds a sidebar to the main screen',
    'description': '''
        This module adds a sidebar to the main screen. The sidebar has a list
        of all installed apps similar to the home menu to ease navigation.
    ''',
    'version': '19.0.1.1.1',
    'category': 'Tools/UI',
    'license': 'LGPL-3', 
    'author': 'MuK IT',
    'website': 'http://www.mukit.at',
    'live_test_url': 'https://youtu.be/kmu69REqKDU',
    'contributors': [
        'Mathias Markl <mathias.markl@mukit.at>',
    ],
    'depends': [
        'base_setup',
        'web',
    ],
    'data': [
        'templates/webclient.xml',
        'views/res_users.xml',
        'views/res_config_settings.xml',
    ],
    'assets': {
        'web._assets_primary_variables': [
            'muk_web_appsbar/static/src/scss/variables.scss',
        ],
        'web._assets_backend_helpers': [
            'muk_web_appsbar/static/src/scss/mixins.scss',
        ],
        'web.assets_web_dark': [
            (
                'after',
                'muk_web_appsbar/static/src/scss/variables.scss',
                'muk_web_appsbar/static/src/scss/variables.dark.scss',
            ),
        ],
        'web.assets_backend': [
            (
                'after',
                'web/static/src/webclient/webclient.js',
                'muk_web_appsbar/static/src/webclient/webclient.js',
            ),
            (
                'after',
                'web/static/src/webclient/webclient.xml',
                'muk_web_appsbar/static/src/webclient/webclient.xml',
            ),
            (
                'after',
                'web/static/src/webclient/webclient.js',
                'muk_web_appsbar/static/src/webclient/menus/app_menu_service.js',
            ),
            (
                'after',
                'web/static/src/webclient/webclient.js',
                'muk_web_appsbar/static/src/webclient/appsbar/appsbar.js',
            ),
            'muk_web_appsbar/static/src/webclient/webclient.scss',
            'muk_web_appsbar/static/src/webclient/appsbar/appsbar.xml',
            'muk_web_appsbar/static/src/webclient/appsbar/appsbar.scss',
        ],
    },
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'post_init_hook': '_setup_module',
}
