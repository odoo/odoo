# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Web Gantt',
    'category': 'Hidden',
    'description': """
Odoo Web Gantt chart view.
=============================

    """,
    'version': '2.0',
    'depends': ['web'],
    'assets': {
        'web._assets_primary_variables': [
            'web_gantt/static/src/gantt_view.variables.scss',
        ],
        'web.assets_backend': [
            'web_gantt/static/src/**/*',

            # Don't include dark mode files in light mode
            ('remove', 'web_gantt/static/src/**/*.dark.scss'),
        ],
        'web.qunit_suite_tests': [
            'web_gantt/static/tests/**/*',
            ('remove', 'web_gantt/static/tests/**/*_mobile_tests.js'),
        ],
        'web.qunit_mobile_suite_tests': [
            'web_gantt/static/tests/helpers.js',
            'web_gantt/static/tests/**/*_mobile_tests.js',
        ],
        # ========= Dark Mode =========
        "web.dark_mode_variables": [
            ('before', 'web_enterprise/static/src/**/*.variables.scss', 'web_gantt/static/src/**/*.variables.dark.scss'),
        ],
        "web.assets_web_dark": [
            'web_gantt/static/src/**/*.dark.scss',
        ],
    },
    'auto_install': True,
    'license': 'OEEL-1',
}
