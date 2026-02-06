{
    'name': "TOTPortal",
    'category': 'Hidden',
    'depends': ['portal', 'auth_totp'],
    'auto_install': True,
    'data': [
        'views/templates.xml',
        'security/ir.access.csv',
    ],
    'assets': {
        'web.assets_frontend': [
            'auth_totp_portal/static/src/**/*',
        ],
        'web.assets_tests': [
            'auth_totp_portal/static/tests/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
