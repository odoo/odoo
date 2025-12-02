{
    'name': 'Passkeys Portal',
    'version': '1.0',
    'summary': 'Passkeys for portal users',
    'description': """
The implementation of Passkeys using the webauthn protocol.
===========================================================

Passkeys are a secure alternative to a username and a password.
When a user logs in with a Passkey, MFA will not be required.
""",
    'category': 'Hidden/Tools',
    'depends': ['auth_passkey', 'portal'],
    'data': [
        'views/templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'auth_passkey_portal/static/src/**',
        ],
        'web.assets_tests': [
            'auth_passkey_portal/static/tests/tours/*.js',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'auto_install': True,
}
