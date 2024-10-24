{
    'name': 'Signup reCAPTCHA',
    'description': """
Implements reCAPTCHA for the signup page
===============================================
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
            'auth_signup_recaptcha/static/**/*',
        ],
    },
    'license': 'LGPL-3',
}
