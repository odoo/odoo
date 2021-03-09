{
    'name': "Password Policy support for Signup",
    'depends': ['auth_password_policy', 'portal'],
    'category': 'Tools',
    'auto_install': True,
    'data': ['views/templates.xml'],
    'assets': {
        'web.assets_frontend': [
            # inside .
            'auth_password_policy_portal/static/src/scss/portal_policy.scss',
        ],
    }
}
