# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


{
    'name': 'Project Management - Reporting',
    'version': '1.0',
    'category': 'Generic Modules/Projects & Services',
    'description': """A module that adds some reports on projects.
    Closed Tasks (By User and By Project), Finished Task (By User and By Project)""",
    'author': 'Tiny',
    'website': 'http://www.openerp.com',
    'depends': ['project', 'report_task'],
    'init_xml': [],
    'update_xml': ['security/ir.model.access.csv', 'report_project_view.xml'],
    'demo_xml': [],
    'installable': True,
    'active': False,
    'certificate': '0086804423149',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
