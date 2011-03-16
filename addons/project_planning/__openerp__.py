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
    'name': 'Planning Management Module',
    'version': '1.0',
    'category': 'Generic Modules/Human Resources',
    'description': """
This module helps you to manage your plannings.
===============================================

This module is based on the analytic accounting and is totally integrated with
* the timesheets encoding
* the holidays management
* the project management

So that, each department manager can know if someone in his team has still unallocated time for a given planning (taking in consideration the validated leaves) or if he still needs to encode tasks.

At the end of the month, the planning manager can also check if the encoded timesheets are respecting the planned time on each analytic account.
""",
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'images': ['images/planning_statistics.jpeg','images/project_planning.jpeg'],
    'depends': [
        'project',
        'hr_timesheet',
        'hr_holidays',
    ],
    'init_xml': [],
    'update_xml': [
        'security/ir.model.access.csv',
        'project_planning_view.xml',
        'project_planning_report.xml',
        'board_project_planning_view.xml',
    ],
    'demo_xml': [
        'project_planning_demo.xml',
    ],
    'test': [
        'test/planning_states.yml',
        'test/project_planning_report.yml'
    ],
    'installable': True,
    'active': False,
    'certificate': '0034901836973',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
