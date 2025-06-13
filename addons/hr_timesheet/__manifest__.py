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
        'views/project_project_views.xml',
        'views/project_task_views.xml',
        'views/project_task_portal_templates.xml',
        'views/hr_timesheet_portal_templates.xml',
        'report/hr_timesheet_report_view.xml',
        'report/project_report_view.xml',
        'report/report_timesheet_templates.xml',
        'views/hr_department_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_employee_public_views.xml',
        'data/hr_timesheet_data.xml',
        'views/project_task_sharing_views.xml',
        'views/project_update_views.xml',
        'wizard/hr_employee_delete_wizard_views.xml',
        'views/hr_timesheet_menus.xml',
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
            ('remove', 'hr_timesheet/static/src/views/project_task_analysis_graph/**/*'),
            ('remove', 'hr_timesheet/static/src/views/project_task_graph/**/*'),
            ('remove', 'hr_timesheet/static/src/views/timesheet_graph/**/*'),
        ],
        'web.assets_backend_lazy': [
            'hr_timesheet/static/src/views/project_task_analysis_graph/**/*',
            'hr_timesheet/static/src/views/project_task_graph/**/*',
            'hr_timesheet/static/src/views/timesheet_graph/**/*',
        ],
        'web.assets_unit_tests': [
            'hr_timesheet/static/tests/hr_timesheet_models.js',
            'hr_timesheet/static/tests/**/*.test.js',
        ],
        'project.webclient': [
            'hr_timesheet/static/src/services/**/*',
            'hr_timesheet/static/src/components/**/*',
            'hr_timesheet/static/src/scss/timesheets_task_form.scss'
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
