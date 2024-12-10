{
    'name': 'Signup Turnstile',
    'description': """
Implements Turnstile for the signup and reset password page.
============================================================
    """,
    'version': '1.0',
    'category': 'Hidden/Tools',
    'auto_install': True,
    'installable': True,
    'depends': [
        'website_cf_turnstile',
        'auth_signup_recaptcha',
    ],
    'assets': {
        'web.assets_frontend': [
            'auth_signup_turnstile/static/src/signup.js',
        ],
    },
    'license': 'LGPL-3',
}
