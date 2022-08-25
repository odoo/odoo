{
    'name': "Password Policy support for Signup",
    'depends': ['auth_password_policy', 'portal'],
    'category': 'Tools',
    'auto_install': True,
    'data': ['views/templates.xml'],
    'assets': {
        'web.assets_frontend': [
            'auth_password_policy_portal/static/**/*',
        ],
    },
    'license': 'LGPL-3',
}
