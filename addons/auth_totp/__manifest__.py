{
    'name': 'Two-Factor Authentication (TOTP)',
    'description': """
Two-Factor Authentication (TOTP)
================================
Allows users to configure two-factor authentication on their user account
for extra security, using time-based one-time passwords (TOTP).

Once enabled, the user will need to enter a 6-digit code as provided
by their authenticator app before being granted access to the system.
All popular authenticator apps are supported.

Note: logically, two-factor prevents password-based RPC access for users
where it is enabled. In order to be able to execute RPC scripts, the user
can setup API keys to replace their main password.
    """,
    'depends': ['web', 'mail'],
    'category': 'Extra Tools',
    'auto_install': True,
    'data': [
        'data/mail_templates_data.xml',
        'security/security.xml',
        'views/user_preferences.xml',
        'views/templates.xml',
    ],
    'assets': {
        'web.assets_tests': [
            'auth_totp/static/tests/**/*',
        ],
        'web.assets_backend': [
            'auth_totp/static/src/**/*',
        ],
    },
    'license': 'LGPL-3',
}
