# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Helpdesk Timesheet',
    'category': 'Services/Helpdesk',
    'summary': 'Project, Tasks, Timesheet',
    'depends': ['timesheet_grid', 'project_helpdesk'],
    'description': """
- Allow to set project for Helpdesk team
- Track timesheet for a task from a ticket
    """,
    'data': [
        'security/ir.model.access.csv',
        'security/helpdesk_timesheet_security.xml',
        'views/helpdesk_team_views.xml',
        'views/helpdesk_ticket_views.xml',
        'views/project_views.xml',
        'views/hr_timesheet_views.xml',
        'wizard/helpdesk_ticket_create_timesheet_views.xml',
        'report/helpdesk_ticket_analysis_views.xml',
        'report/report_timesheet_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'helpdesk_timesheet/static/src/**/*',
        ],
        'web.qunit_suite_tests': [
            "helpdesk_timesheet/static/tests/*",
        ],
    },
    'demo': ['data/helpdesk_timesheet_demo.xml'],
    'license': 'OEEL-1',
    'post_init_hook': '_helpdesk_timesheet_post_init',
    'uninstall_hook': '_helpdesk_timesheet_uninstall',
}
