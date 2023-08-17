{
    'name': "Password Policy",
    "summary": "Implement basic password policy configuration & check",
    'category': 'Hidden/Tools',
    'depends': ['base_setup', 'web', 'bus'],
    'data': [
        'data/defaults.xml',
        'views/res_users.xml',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'auth_password_policy/static/src/password_meter.js',
            'auth_password_policy/static/src/password_field.js',
            'auth_password_policy/static/src/password_field.xml',
        ],
        'web.assets_frontend': [
            'auth_password_policy/static/src/css/password_field.css',
            'auth_password_policy/static/src/password_policy.js',
            'auth_password_policy/static/src/password_leak_check.js',
            'auth_password_policy/static/src/login.js',
            'auth_password_policy/static/src/change_password.js',
        ],
        'web.assets_common': [
            'auth_password_policy/static/src/simple_tagged_notification_service.js',
            'auth_password_policy/static/src/css/password_field.css',
            'auth_password_policy/static/src/password_policy.js',
            'auth_password_policy/static/src/password_leak_check.js',
            'auth_password_policy/static/src/change_password.js',
        ],
    },
    'license': 'LGPL-3',
}
