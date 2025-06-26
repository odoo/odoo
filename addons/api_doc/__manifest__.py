{
    'name': 'API Documentation',
    'category': 'Hidden',
    'version': '1.0',
    'description': """
Odoo Dynamic API Documentation
==============================

This module provides a dynamic documentation page for developpers at the
/doc URL. The documentation is generated using the database to lists the
models and their fields and methods. It also provide a playground to run
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
            # Libs
            'web/static/src/libs/fontawesome/css/font-awesome.css',
            'web/static/src/scss/fontawesome_overridden.scss',

            # Core
            'web/static/src/module_loader.js',
            'web/static/lib/owl/owl.js',
            'web/static/lib/owl/odoo_module.js',

            # Utils
            'web/static/src/core/utils/functions.js',
            'web/static/src/core/utils/reactive.js',
            'web/static/src/core/browser/browser.js',
            'web/static/src/core/utils/timing.js',
            'web/static/src/core/template_inheritance.js',
            'web/static/src/core/templates.js',
            'web/static/src/core/registry.js',
            'web/static/src/session.js',
            'web/static/src/core/assets.js',
            'web/static/src/core/code_editor/**',

            'api_doc/static/src/**/*',
        ],
    },
    'bootstrap': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
