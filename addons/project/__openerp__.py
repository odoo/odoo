# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Project Management',
    'version': '1.1',
    'author': 'OpenERP SA',
    'website': 'https://www.odoo.com/page/project-management',
    'category': 'Project Management',
    'sequence': 8,
    'summary': 'Projects, Tasks',
    'depends': [
        'base_setup',
        'product',
        'analytic',
        'board',
        'mail',
        'resource',
        'web_kanban',
        'web_tip',
        'web_planner',
    ],
    'description': """
Track multi-level projects, tasks, work done on tasks
=====================================================

This application allows an operational project management system to organize your activities into tasks and plan the work you need to get the tasks completed.

Gantt diagrams will give you a graphical representation of your project plans, as well as resources availability and workload.

Dashboard / Reports for Project Management will include:
--------------------------------------------------------
* My Tasks
* Open Tasks
* Tasks Analysis
* Cumulative Flow
    """,
    'data': [
        'security/project_security.xml',
        'wizard/project_task_delegate_view.xml',
        'security/ir.model.access.csv',
        'project_data.xml',
        'project_view.xml',
        'res_partner_view.xml',
        'report/project_report_view.xml',
        'report/project_cumulative.xml',
        'res_config_view.xml',
        'views/project.xml',
        'project_tip_data.xml',
        'project_dashboard.xml',
        'web_planner_data.xml',
    ],
    'demo': ['project_demo.xml'],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
