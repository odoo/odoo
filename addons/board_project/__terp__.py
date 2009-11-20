# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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
    'name': 'Board for project users',
    'version': '1.0',
    'category': 'Board/Projects & Services',
    'description': """
This module implements a dashboard for project member that includes:
    * List of my open tasks
    * List of my next deadlines
    * List of public notes
    * Graph of my timesheet
    * Graph of my work analysis
    """,
    'author': 'Tiny',
    'depends': [
        'project',
        'report_timesheet',
        'board',
        'report_analytic_planning',
        'report_analytic_line',
        'report_task',
        'hr_timesheet_sheet'
    ],
    'update_xml': ['board_project_view.xml', 'board_project_manager_view.xml'],
    'demo_xml': ['board_project_demo.xml'],
    'installable': True,
    'active': False,
    'certificate': '0039350482013',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
