{
    'name': 'Passkeys',
    'version': '1.0',
    'summary': 'Log in with a Passkey',
    'description': """
The implementation of Passkeys using the webauthn protocol.
===========================================================

Passkeys are a secure alternative to a username and a password.
When a user logs in with a Passkey, MFA will not be required.
""",
    'category': 'Hidden/Tools',
    'depends': ['base_setup', 'web'],
    'data': [
        'views/auth_passkey_key_views.xml',
        'views/auth_passkey_login_templates.xml',
        'views/res_users_identitycheck_views.xml',
        'views/res_users_views.xml',
        'security/ir.model.access.csv',
        'security/security.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'auth_passkey/static/src/views/*',
            'auth_passkey/static/lib/simplewebauthn.js',
        ],
        'web.assets_frontend': [
            'auth_passkey/static/lib/simplewebauthn.js',
            'auth_passkey/static/src/login_passkeys.js',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
}
