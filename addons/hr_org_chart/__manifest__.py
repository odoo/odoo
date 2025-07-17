# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'HR Org Chart',
    'category': 'Human Resources',
    'version': '1.0',
    'description':
        """
Org Chart Widget for HR
=======================

This module extend the employee form with a organizational chart.
(N+1, N+2, direct subordinates)
        """,
    'depends': ['hr', 'web_hierarchy'],
    'auto_install': ['hr'],
    'data': [
        'views/hr_department_views.xml',
        'views/hr_employee_public_views.xml',
        'views/hr_views.xml',
    ],
    'assets': {
        'web._assets_primary_variables': [
            'hr_org_chart/static/src/scss/variables.scss',
        ],
        'web.assets_backend': [
            'hr_org_chart/static/src/fields/*',
        ],
        'web.assets_backend_lazy': [
            'hr_org_chart/static/src/views/**/*',
        ],
        'web.assets_tests': [
            'hr_org_chart/static/tests/tours/*.js',
        ],
        'web.assets_unit_tests': [
            'hr_org_chart/static/tests/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
