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
            ('remove', 'auth_password_policy/static/src/css/password_field.css'),
        ],
        'web.assets_frontend': [
            'auth_password_policy/static/src/css/password_field.css',
            'auth_password_policy/static/src/password_policy.js',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
