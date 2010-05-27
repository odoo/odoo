# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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
    'name': 'Issue Management in Project Management',
    'version': '1.0',
    'category': 'Generic Modules/CRM & SRM',
    'description': """
        This module provide Issues/Bugs Management in Project
    """,
    'author': 'Tiny',
    'website': 'http://www.openerp.com',
    'depends': [
        'project',
        'hr_timesheet_sheet',
    ],
    'init_xml': [
        'project_issue_data.xml'
    ],
    'update_xml': [
        'project_issue_view.xml',
        'project_issue_menu.xml',
        'report/project_issue_report_view.xml',
        'security/project_issue_security.xml',
        'security/ir.model.access.csv',
     ],
    'demo_xml': ['project_issue_demo.xml'],
    'installable': True,
    'active': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
