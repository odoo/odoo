{
    'name': 'Accounting Import',
    'description': """
Enable import menus for Accounting
======================================
""",
    'depends': ['base_import', 'account'],
    'version': '1.0',
    'category': 'Hidden/Tools',
    'installable': True,
    'auto_install': True,
    'data': [
        'views/account_account_views.xml',
        'views/account_menuitem.xml',
    ],
    'assets': {
        'web.assets_qweb': [
            'base_import_account/static/src/**/*.xml',
        ],
        'web.assets_backend': [
            'base_import_account/static/src/**/*.js',
        ],
        'web.qunit_suite_tests': [
        ],
    },
    'license': 'LGPL-3',
}
