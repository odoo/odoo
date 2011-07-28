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
    "name": "Project Management",
    "version": "1.1",
    "author": "OpenERP SA",
    "website": "http://www.openerp.com",
    "category": "Project Management",
    'complexity': "easy",
    "images": ["images/gantt.png", "images/project_dashboard.jpeg","images/project_task_tree.jpeg","images/project_task.jpeg","images/project.jpeg","images/task_analysis.jpeg"],
    "depends": ["base_setup", "product", "analytic", "board"],
    "description": """
Project management module tracks multi-level projects, tasks, work done on tasks, eso.
======================================================================================

It is able to render planning, order tasks, eso.

Dashboard for project members that includes:
--------------------------------------------
    * List of my open tasks
    * List of my delegated tasks
    * Graph of My Projects: Planned vs Total Hours
    * Graph of My Remaining Hours by Project
    """,
    "init_xml": [],
    "update_xml": [
        "security/project_security.xml",
        "wizard/project_task_delegate_view.xml",
        "wizard/project_task_close_view.xml",
        "wizard/project_task_reevaluate_view.xml",
        "security/ir.model.access.csv",
        "project_data.xml",
        "project_view.xml",
        "process/task_process.xml",
        "project_installer.xml",
        "res_partner_view.xml",
        "report/project_report_view.xml",
        "board_project_view.xml",
        'board_project_manager_view.xml'
    ],
    'demo_xml': [
        'project_demo.xml',
        'board_project_demo.xml',
    ],
    'test':[
        'test/test_project.yml',
        'test/test_project_delegation.yml',
    ],
    'installable': True,
    'active': False,
    'certificate': '0075116868317',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
