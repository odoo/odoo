# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Task Logs',
    'version': '1.0',
    'category': 'Services/Timesheets',
    'sequence': 23,
    'summary': 'Track employee time on tasks',
    'description': """
This module implements a timesheet system.
==========================================

Each employee can encode and track their time spent on the different projects.

Lots of reporting on time and employee tracking are provided.

It is completely integrated with the cost accounting module. It allows you to set
up a management by affair.
    """,
    'website': 'https://www.odoo.com/app/timesheet',
    'depends': ['hr', 'hr_hourly_cost', 'analytic', 'project', 'uom'],
    'data': [
        'security/hr_timesheet_security.xml',
        'security/ir.model.access.csv',
        'security/ir.model.access.xml',
        'data/digest_data.xml',
        'views/hr_timesheet_views.xml',
        'views/res_config_settings_views.xml',
        'views/project_views.xml',
        'views/project_portal_templates.xml',
        'views/hr_timesheet_portal_templates.xml',
        'report/hr_timesheet_report_view.xml',
        'report/project_report_view.xml',
        'report/report_timesheet_templates.xml',
        'views/hr_views.xml',
        'data/hr_timesheet_data.xml',
        'views/project_sharing_views.xml',
        'views/rating_rating_views.xml',
        'views/project_update_views.xml',
    ],
    'demo': [
        'data/hr_timesheet_demo.xml',
    ],
    'installable': True,
    'post_init_hook': 'create_internal_project',
    'uninstall_hook': '_uninstall_hook',
    'assets': {
        'web.assets_backend': [
            'hr_timesheet/static/src/**/*',
        ],
        'web.qunit_suite_tests': [
            'hr_timesheet/static/tests/**/*',
        ],
        'project.webclient': [
            'hr_timesheet/static/src/components/**/*',
            'hr_timesheet/static/src/scss/timesheets_task_form.scss'
        ],
    },
    'license': 'LGPL-3',
}
