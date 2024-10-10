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
            'auth_password_policy/static/src/**/*',
        ],
    },
    'license': 'LGPL-3',
}
