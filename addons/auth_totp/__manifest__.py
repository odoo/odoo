{
    'name': 'Two-Factor Authentication (TOTP)',
    'description': """
Two-Factor Authentication (TOTP)
================================
Allows users to configure two-factor authentication on their user account
for extra security and invite another user to use Two-Factor authentication
by sending an email to the target user, using time-based one-time passwords (TOTP).

Once enabled, the user will need to enter a 6-digit code as provided
by their authenticator app before being granted access to the system.
All popular authenticator apps are supported.

Key Features
------------
* Allow users to add TOTP via their user prefs
* Allow OTP via email for logins
* Allow admins to force all users to use OTP or TOTP
* Allow admins to invite users to enable TOTP
* Sends email notification when 'allowed device' is added

Note: logically, two-factor prevents password-based RPC access for users
where it is enabled. In order to be able to execute RPC scripts, the user
can setup API keys to replace their main password.
    """,
    'depends': ['web', 'mail'],
    'category': 'Extra Tools',
    'auto_install': True,
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ir_action_data.xml',
        'data/mail_template_data.xml',
        'data/security_notifications_template.xml',
        'views/res_config_settings_views.xml',
        'views/res_users_views.xml',
        'views/templates.xml',
        'wizard/auth_totp_wizard_views.xml',
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
