# -*- coding: utf-8 -*-
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
    'name': 'Human Resources (Timesheet encoding)',
    'version': '1.0',
    'category': 'Generic Modules/Human Resources',
    'description': """
This module implement a timesheet system. Each employee can encode and
track their time spent on the different projects. A project is an
analytic account and the time spent on a project generate costs on
the analytic account.

Lots of reporting on time and employee tracking are provided.

It is completely integrated with the cost accounting module. It allows you
to set up a management by affair.
    """,
    'author': 'Tiny',
    'website': 'http://www.openerp.com',
    'depends': ['account', 'hr', 'base', 'hr_attendance', 'process'],
    'init_xml': ['hr_timesheet_data.xml'],
    'update_xml': [
        'security/ir.model.access.csv',
        'hr_timesheet_view.xml',
        'hr_timesheet_report.xml',
        'hr_timesheet_wizard.xml',
        'process/hr_timesheet_process.xml'
    ],
    'demo_xml': ['hr_timesheet_demo.xml'],
    'installable': True,
    'active': False,
    'certificate': '0071405533469',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
