# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Timesheet on Project',
    'category': 'Project',
    'description': """
Timesheet on project and task to track employee time.
""",
    'depends': ['project', 'hr_timesheet'],
    'data': [
        'views/analytic_views.xml',
        'views/hr_timesheet_views.xml',
        'views/project_views.xml',
        'views/project_portal_templates.xml',
        'report/project_report_views.xml',
        'report/timesheet_report_views.xml',
        'report/report_timesheet_templates.xml',
        'security/ir.model.access.csv',
        'security/project_timesheet_security.xml',
        'data/project_timesheet_data.xml',
    ],
    'demo': [
        'data/project_timesheet_demo.xml',
    ],
    'auto_install': True,
}
