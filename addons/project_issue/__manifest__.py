# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Issue Tracking',
    'version': '1.0',
    'category': 'Project',
    'sequence': 40,
    'summary': 'Support, Bug Tracker, Helpdesk',
    'description': """
Track Issues/Bugs Management for Projects
=========================================
This application allows you to manage the issues you might face in a project like bugs in a system, client complaints or material breakdowns.

It allows the manager to quickly check the issues, assign them and decide on their status quickly as they evolve.
    """,
    'website': 'https://www.odoo.com/page/project-management',
    'depends': [
        'project',
    ],
    'data': [
        'data/mail_message_subtype_data.xml',
        'report/project_issue_report_views.xml',
        'security/project_issue_security.xml',
        'security/ir.model.access.csv',
        'views/project_issue_views.xml',
        'views/account_analytic_account_views.xml',
        'views/project_project_views.xml',
        'views/res_partner_views.xml',
        'views/project_config_settings_views.xml',
    ],
    'demo': ['data/project_issue_demo.xml'],
    'application': True,
}
