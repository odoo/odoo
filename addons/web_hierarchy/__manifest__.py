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
        'web.assets_backend_lazy': [
            'web_hierarchy/static/src/**/*',
            ('remove', 'web_hierarchy/static/src/hierarchy.variables.dark.scss'),
        ],
        'web.assets_backend_lazy_dark': [
            ('before', 'web_hierarchy/static/src/hierarchy.variables.scss', 'web_hierarchy/static/src/hierarchy.variables.dark.scss'),
        ],
        'web.assets_unit_tests': [
            'web_hierarchy/static/tests/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
