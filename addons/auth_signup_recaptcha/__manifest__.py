{
    'name': 'Signup reCAPTCHA',
    'description': """
Implements reCAPTCHA for the signup and reset password page.
============================================================
    """,
    'version': '1.0',
    'category': 'Hidden/Tools',
    'auto_install': True,
    'installable': True,
    'depends': [
        'google_recaptcha',
        'auth_signup',
    ],
    'assets': {
        'web.assets_frontend': [
            'auth_signup_recaptcha/static/src/signup.js',
        ],
    },
    'license': 'LGPL-3',
}
