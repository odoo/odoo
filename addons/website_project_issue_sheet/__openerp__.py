# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Timesheet on Website Project Issue',
    'version': '0.1',
    'category': 'Tools',
    'complexity': 'easy',
    'description': """
Add timesheet support on issue in the frontend.
==================================================================================================
    """,
    'depends': ['website_project_issue', 'project_issue_sheet'],
    'data': [
        'views/project_issue_templates.xml',
        'security/ir.model.access.csv',
        'security/portal_security.xml',
    ],
    'installable': True,
    'auto_install': True,
    'category': 'Hidden',
}
