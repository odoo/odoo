{
    'name': 'API Documentation',
    'category': 'Hidden',
    'description': """
Odoo Dynamic API Documentation
==============================

This module provides a dynamic documentation page for developpers at the
/doc URL. The documentation is generated using the database to list the
models and their fields and methods. It also provides a playground to run
the methods over HTTP, with examples in various programming languages.
""",
    'depends': ['web'],
    'auto_install': True,
    'data': [
        'security/res_groups.xml',
        'views/docclient.xml',
    ],
    'assets': {
        'api_doc.assets': [
            ('include', 'web.icons_fonts'),
            ('include', 'web._assets_helpers'),
            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',
            'web/static/lib/bootstrap/scss/_variables-dark.scss',
            'web/static/lib/bootstrap/scss/_maps.scss',

            ('include', 'web._assets_bootstrap'),
            ('include', 'web._assets_core'),
            'web/static/src/core/code_editor/**',

            'api_doc/static/src/**/*.xml',
            'api_doc/static/src/**/*.js',
            'api_doc/static/src/doc_client.css',
            ('remove', 'api_doc/static/src/api_action.js'),
        ],
        'web.assets_unit_tests': [
            'api_doc/static/src/**/*.xml',
            'api_doc/static/src/**/*.js',
            'api_doc/static/src/doc_client.css',
            ('remove', 'api_doc/static/src/api_action.js'),
            ('remove', 'api_doc/static/src/main.js'),
            'api_doc/static/tests/**/*.test.js',
            'api_doc/static/tests/doc_test_helpers.js',
        ],
        'web.assets_backend': [
            'api_doc/static/src/api_action.js',
        ],
    },
    'bootstrap': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
