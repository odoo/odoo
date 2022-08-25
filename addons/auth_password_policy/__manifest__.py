{
    'name': "Password Policy",
    "summary": "Implement basic password policy configuration & check",
    'category': 'Hidden/Tools',
    'depends': ['base_setup', 'web'],
    'data': [
        'data/defaults.xml',
        'views/res_users.xml',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'auth_password_policy/static/src/js/password_field.js',
            'auth_password_policy/static/src/js/change_password.js',
        ],
        'web.assets_common': [
            'auth_password_policy/static/src/js/password_gauge.js',
            'auth_password_policy/static/src/css/password_field.css',
        ],
    },
    'license': 'LGPL-3',
}
