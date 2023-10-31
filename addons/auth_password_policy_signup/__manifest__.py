{
    'name': "Password Policy support for Signup",
    'depends': ['auth_password_policy', 'auth_signup'],
    'category': 'Hidden/Tools',
    'auto_install': True,
    'data': [
        'views/signup_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'auth_password_policy_signup/static/**/*',
        ],
    },
    'license': 'LGPL-3',
}
