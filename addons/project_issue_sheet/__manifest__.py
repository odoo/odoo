# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Timesheet on Issues',
    'version': '1.0',
    'category': 'Project',
    'description': """
This module adds the Timesheet support for the Issues/Bugs Management in Project.
=================================================================================

Worklogs can be maintained to signify number of hours spent by users to handle an issue.
                """,
    'website': 'https://www.odoo.com/page/project-management',
    'depends': [
        'project_issue',
        'hr_timesheet_sheet',
    ],
    'data': [
        'views/project_issue_view.xml',
        'security/ir.model.access.csv',
        'security/portal_security.xml',
    ],
    'auto_install': True,
}
