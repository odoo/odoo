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
            'auth_totp_portal/static/src/js/totp_frontend.js',
            'auth_totp_portal/static/src/scss/auth_totp_portal.scss',
        ],
        'web.assets_tests': [
            'auth_totp_portal/static/tests/**/*',
        ],
    },
    'license': 'LGPL-3',
}
