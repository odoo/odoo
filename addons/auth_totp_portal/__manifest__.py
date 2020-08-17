{
    'name': "TOTPortal",
    'category': 'Hidden',
    'depends': ['portal', 'auth_totp'],
    'auto_install': True,
    'data': [
        'security/security.xml',
        'views/templates.xml',
    ],
}
