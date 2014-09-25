# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'Project Management',
    'version': '1.1',
    'author': 'OpenERP SA',
    'website': 'https://www.odoo.com/page/project-management',
    'category': 'Project Management',
    'sequence': 8,
    'summary': 'Projects, Tasks',
    'images': [
        'images/gantt.png',
        'images/project_task_tree.jpeg',
        'images/project_task.jpeg',
        'images/project.jpeg',
        'images/task_analysis.jpeg',
        'images/project_kanban.jpeg',
        'images/task_kanban.jpeg',
        'images/task_stages.jpeg'
    ],
    'depends': [
        'base_setup',
        'product',
        'analytic',
        'board',
        'mail',
        'resource',
        'web_kanban',
        'web_kanban_sparkline'
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
    ],
    'demo': ['project_demo.xml'],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
