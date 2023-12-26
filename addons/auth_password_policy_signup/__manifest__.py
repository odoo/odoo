{
    'name': "Password Policy support for Signup",
    'depends': ['auth_password_policy', 'auth_signup'],
    'category': 'Hidden/Tools',
    'auto_install': True,
    'data': [
        'views/assets.xml',
        'views/signup_templates.xml',
    ],
    'license': 'LGPL-3',
}
