{
    'name': 'Kitworks API',
    'version': '16.0.1.2.3',
    'license': 'LGPL-3',
    'category': 'KW API',

    'author': 'Kitworks Systems',
    'website': 'https://kitworks.systems/',

    'images': [
        'static/description/cover.png',
        'static/description/icon.png',
    ],

    'depends': [
        'base',
        'mail',
        'kw_mixin',
    ],

    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',

        'data/ir.cron.xml',

        'views/api_main_menu_views.xml',

        'views/api_log_views.xml',
        'views/api_token_views.xml',
        'views/api_key_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_users_views.xml',
    ],

    'installable': True,
}
