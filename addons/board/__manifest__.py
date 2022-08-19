# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Dashboards',
    'version': '1.0',
    'category': 'Productivity',
    'sequence': 225,
    'summary': 'Build your own dashboards',
    'description': """
Lets the user create a custom dashboard.
========================================

Allows users to create custom dashboard.
    """,
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/board_views.xml',
        ],
    'application': True,
    'assets': {
        'web.assets_backend': [
            'board/static/src/**/*.scss',
            'board/static/src/**/*.js',
            'board/static/src/**/*.xml',
        ],
        'web.qunit_suite_tests': [
            'board/static/tests/**/*',
        ],
    },
    'license': 'LGPL-3',
}
