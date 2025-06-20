{
    'name': 'Doc',
    'category': 'Hidden',
    'version': '1.0',
    'description': """
Odoo Doc module.
========================

This module provides a dynamic documentation page for all python models.
""",
    'depends': ['web'],
    'auto_install': True,
    'data': [
        'security/res_groups.xml',
        'views/docclient.xml',
    ],
    'assets': {
        'doc.assets': [
            # Libs
            'web/static/src/libs/fontawesome/css/font-awesome.css',
            'web/static/src/scss/fontawesome_overridden.scss',
            ('include', 'web.ace_lib'),

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

            'doc/static/src/**/*',
        ],
    },
    'bootstrap': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
