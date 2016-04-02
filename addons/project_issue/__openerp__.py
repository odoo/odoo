# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Issue Tracking',
    'version': '1.0',
    'category': 'Project Management',
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
        'sales_team',
        'project',
    ],
    'data': [
        'project_issue_view.xml',
        'project_issue_menu.xml',
        'report/project_issue_report_view.xml',
        'security/project_issue_security.xml',
        'security/ir.model.access.csv',
        'project_issue_data.xml',
        'project_dashboard.xml',
     ],
    'demo': ['project_issue_demo.xml'],
    'test': [
        'test/issue_users.yml',
        'test/subscribe_issue.yml',
        'test/issue_process.yml',
        'test/issue_demo.yml'
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
