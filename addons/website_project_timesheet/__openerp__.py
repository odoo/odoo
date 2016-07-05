# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Timesheet on Website Project',
    'category': 'Website',
    'description': """
Add timesheet support on task in the frontend.
==================================================================================================
    """,
    'depends': ['website_project', 'hr_timesheet'],
    'data': [
        'security/ir.model.access.csv',
        'security/portal_security.xml',
        'views/website_project_templates.xml',
    ],
    'auto_install': True,
}
