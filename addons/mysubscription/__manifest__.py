{
    'name': 'My Subscription',
    'summary': 'Backend Subscription App',
    'category': 'Sales',
    'license': 'LGPL-3',
    'author': 'Odoo S.A.',
    'depends': ['base', 'web'],
    'auto_install': True,
    'data': [
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'mysubscription/static/src/**/*.js',
            'mysubscription/static/src/**/*.xml',
            'mysubscription/static/src/**/*.scss',
        ],
        'web.assets_unit_tests': [
            'mysubscription/static/tests/**/*',
        ],
    },
}
