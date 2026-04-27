# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Planning",
    'summary': """Manage your employees' schedule""",
    'description': """
Schedule your teams and employees with shift.
    """,
    'category': 'Human Resources/Planning',
    'sequence': 130,
    'version': '1.0',
    'depends': ['hr', 'hr_hourly_cost', 'web_gantt', 'digest'],
    'data': [
        'security/planning_security.xml',
        'security/ir.model.access.csv',
        'data/digest_data.xml',
        'wizard/planning_send_views.xml',
        'views/hr_views.xml',
        'views/planning_template_views.xml',
        'views/resource_views.xml',
        'views/planning_views.xml',
        'views/planning_report_views.xml',
        'views/res_config_settings_views.xml',
        'views/planning_templates.xml',
        'report/planning_report_templates.xml',
        'report/planning_report_views.xml',
        'data/planning_cron.xml',
        'data/mail_template_data.xml',
        'data/planning_tour.xml',
    ],
    'demo': [
        'data/planning_demo.xml',
    ],
    'application': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'planning/static/src/components/**/*',
            'planning/static/src/views/**/*',
            'planning/static/src/scss/planning_gantt.scss',
            'planning/static/src/scss/planning_list.scss',
            'planning/static/src/js/tours/planning.js',
            ('remove', 'planning/static/src/views/planning_graph/**'),
            ('remove', 'planning/static/src/views/planning_pivot/**'),
            ('remove', 'planning/static/src/views/planning_gantt/**'),
        ],
        'web.assets_backend_lazy': [
            'planning/static/src/views/planning_graph/**',
            'planning/static/src/views/planning_pivot/**',
            'planning/static/src/views/planning_gantt/**',
        ],
        'web.assets_frontend': [
            'planning/static/src/scss/planning_calendar_report.scss',
            'planning/static/src/js/planning_calendar_front.js',
        ],
        'web.assets_unit_tests': [
            'planning/static/tests/**/*',
            ('remove', 'planning/static/tests/legacy/**/*'),  # to remove when all legacy tests are ported
        ],
        'web.qunit_suite_tests': [
            'planning/static/tests/legacy/**/*',
        ],
        'web.assets_tests': [
            'planning/static/tests/tours/*',
        ],
    }
}
