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
    'name': 'Report on tasks by user for projects',
    'version': '1.0',
    'category': 'Generic Modules/Projects & Services',
    'description': """Gives statistics on tasks by user on projects to check the pipeline of users.""",
    'author': 'Tiny',
    'depends': ['base', 'project','hr_timesheet_sheet'],
    'init_xml': [],
    'update_xml': ['security/ir.model.access.csv', 'report_task_view.xml'],
    'installable': True,
    'active': False,
    'certificate': '0027671328157',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
