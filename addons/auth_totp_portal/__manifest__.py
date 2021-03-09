{
    'name': "TOTPortal",
    'category': 'Hidden',
    'depends': ['portal', 'auth_totp'],
    'auto_install': True,
    'data': [
        'security/security.xml',
        'views/templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            # inside .
            'auth_totp_portal/static/src/js/totp_frontend.js',
        ],
        'web.assets_tests': [
            # inside .
            'auth_totp_portal/static/tests/totp_portal.js',
        ],
    }
}
