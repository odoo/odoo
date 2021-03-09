{
    'name': "Password Policy support for Signup",
    'depends': ['auth_password_policy', 'auth_signup'],
    'category': 'Hidden/Tools',
    'auto_install': True,
    'data': [
        'views/signup_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            # inside .
            'auth_password_policy_signup/static/src/js/signup_policy.js',
            # inside .
            'auth_password_policy_signup/static/src/scss/signup_policy.scss',
        ],
    }
}
