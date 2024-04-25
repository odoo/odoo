{
    'name': 'Passkeys support for 2FA',
    'version': '1.0',
    'category': 'Hidden/Tools',
    'depends': ['auth_passkey', 'auth_totp'],
    'data': [
        'views/res_users_views.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
