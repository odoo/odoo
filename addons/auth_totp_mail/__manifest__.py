{
    'name': '2FA Invite mail',
    'description': """
2FA Invite mail
===============
Allow the users to invite another user to use Two-Factor authentication
by sending an email to the target user. This email redirects them to:
- the users security settings if the user is internal.
- the portal security settings page if the user is not internal.
    """,
    'depends': ['auth_totp', 'mail'],
    'category': 'Extra Tools',
    'auto_install': True,
    'data': [
        'data/ir_action_data.xml',
        'data/mail_template_data.xml',
        'data/security_notifications_template.xml',
        'views/res_users_views.xml',
    ],
    'assets': {
        'web.assets_tests': [
            'auth_totp_mail/static/tests/**/*',
        ],
    },
    'license': 'LGPL-3',
}
