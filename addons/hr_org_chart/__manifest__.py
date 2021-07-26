# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'HR Org Chart',
    'category': 'Hidden',
    'version': '1.0',
    'description':
        """
Org Chart Widget for HR
=======================

This module extend the employee form with a organizational chart.
(N+1, N+2, direct subordinates)
        """,
    'depends': ['hr'],
    'auto_install': True,
    'data': [
        'views/hr_views.xml'
    ],
    'assets': {
        'web._assets_primary_variables': [
            'hr_org_chart/static/src/scss/variables.scss',
        ],
        'web.assets_backend': [
            'hr_org_chart/static/src/scss/hr_org_chart.scss',
            'hr_org_chart/static/src/js/hr_org_chart.js',
        ],
        'web.qunit_suite_tests': [
            'hr_org_chart/static/tests/**/*',
        ],
        'web.assets_qweb': [
            'hr_org_chart/static/src/xml/**/*',
        ],
    },
    'license': 'LGPL-3',
}
