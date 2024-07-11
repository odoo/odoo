# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Web Hierarchy',
    'category': 'Hidden',
    'version': '1.0',
    'description':
        """
Odoo Web Hierarchy view
=======================

This module adds a new view called to be able to define a view to display
an organization such as an Organization Chart for employees for instance.
        """,
    'depends': ['web'],
    'assets': {
        'web.assets_backend': [
            'web_hierarchy/static/src/hierarchy.variables.scss',
            'web_hierarchy/static/src/**/*',
        ],
        'web.assets_web_dark': [
            ('before', 'web_hierarchy/static/src/hierarchy.variables.scss', 'web_hierarchy/static/src/**/*.variables.dark.scss'),
        ],
        'web.qunit_suite_tests': [
            'web_hierarchy/static/tests/**/*',
        ],
    },
    'license': 'LGPL-3',
}
