# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Timesheet in Website Portal',
    'category': 'Website',
    'description': """
Display Timesheet on Task in the Website Portal
===============================================
    """,
    'depends': ['website_project', 'hr_timesheet'],
    'data': [
        'security/ir.model.access.csv',
        'security/account_analytic_line_security.xml',
        'views/account_analytic_line_templates.xml',
    ],
    'auto_install': True,
}
