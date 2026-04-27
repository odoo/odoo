# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Field Service",
    'summary': "Schedule and track onsite operations, time and material",
    'description': """
Field Services Management
=========================
This module adds the features needed for a modern Field service management.
It installs the following apps:
- Project
- Timesheet

Adds the following options:
- reports on tasks
- FSM app with custom view for onsite worker
- add products on tasks

    """,
    'category': 'Services/Field Service',
    'sequence': 170,
    'version': '1.0',
    'depends': ['project_enterprise', 'timesheet_grid', 'base_geolocalize'],
    'data': [
        'data/fsm_data.xml',
        'data/industry_fsm_tour.xml',
        'security/fsm_security.xml',
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/hr_timesheet_views.xml',
        'views/fsm_views.xml',
        'views/project_task_views.xml',
        'report/project_report_views.xml',
        'report/worksheet_custom_report_templates.xml',
        'report/worksheet_custom_reports.xml',
        'views/res_partner_views.xml',
        'views/project_sharing_views.xml',
        'views/project_portal_templates.xml',
        'data/mail_template_data.xml',
        'wizard/task_stop_timer_wizard_views.xml'
    ],
    'application': True,
    'demo': ['data/fsm_demo.xml'],
    'post_init_hook': 'create_field_service_project',
    'assets': {
        'web.assets_backend': [
            'industry_fsm/static/src/**/*',
            ('remove', 'industry_fsm/static/src/views/fsm_my_task_map/**'),
            ('remove', 'industry_fsm/static/src/views/industry_fsm_grid/**'),
            ('remove', 'industry_fsm/static/src/views/fsm_task_gantt/**'),
            ('remove', 'industry_fsm/static/src/fsm_gantt_controller.js'),
            ('remove', 'industry_fsm/static/src/views/fsm_my_task_activity/**'),
        ],
        'web.assets_backend_lazy': [
            'industry_fsm/static/src/views/fsm_my_task_map/**',
            'industry_fsm/static/src/views/industry_fsm_grid/**',
            'industry_fsm/static/src/views/fsm_task_gantt/**',
            'industry_fsm/static/src/fsm_gantt_controller.js',
            'industry_fsm/static/src/views/fsm_my_task_activity/**',
        ],
        'web.assets_frontend': [
            'industry_fsm/static/src/js/tours/**/*',
        ],
        'web.assets_unit_tests': [
            'industry_fsm/static/tests/**/*.test.js',
        ],
        'web.assets_tests': [
            'industry_fsm/static/tests/tours/**/*',
        ],
    },
    'license': 'OEEL-1',
}
