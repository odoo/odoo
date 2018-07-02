# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Project',
    'version': '1.1',
    'website': 'https://www.odoo.com/page/project-management',
    'category': 'Project',
    'sequence': 10,
    'summary': 'Projects, Tasks',
    'depends': [
        'base_setup',
        'product',
        'analytic',
        'mail',
        'resource',
        'web_kanban',
        'web_planner',
        'web_tour',
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
        'security/ir.model.access.csv',
        'report/project_report_views.xml',
        'views/project_views.xml',
        'views/res_partner_views.xml',
        'views/res_config_views.xml',
        'views/project_templates.xml',
        'views/tour_views.xml',
        'data/web_planner_data.xml',
        'data/project_mail_template_data.xml',
        'data/project_data.xml',
    ],
    'qweb': ['static/src/xml/project.xml'],
    'demo': ['data/project_demo.xml'],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
