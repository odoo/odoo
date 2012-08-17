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
    'name': 'Timesheets',
    'version': '1.0',
    'category': 'Human Resources',
    'description': """
This module implements a timesheet system.
==========================================

Each employee can encode and track their time spent on the different projects.
A project is an analytic account and the time spent on a project generates costs on
the analytic account.

Lots of reporting on time and employee tracking are provided.

It is completely integrated with the cost accounting module. It allows you to set
up a management by affair.
    """,
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'images': ['images/hr_timesheet_lines.jpeg'],
    'depends': ['account', 'hr', 'base', 'hr_attendance', 'process'],
    'data': ['hr_timesheet_data.xml'],
    'data': [
        'security/ir.model.access.csv',
        'security/hr_timesheet_security.xml',
        'hr_timesheet_view.xml',
        'hr_timesheet_report.xml',
        'hr_timesheet_wizard.xml',
        'process/hr_timesheet_process.xml',
        'wizard/hr_timesheet_print_employee_view.xml',
        'wizard/hr_timesheet_print_users_view.xml',
        'wizard/hr_timesheet_sign_in_out_view.xml',
        'hr_timesheet_installer.xml',
    ],
    'demo': ['hr_timesheet_demo.xml'],
    'test': [
        'test/test_hr_timesheet.yml',
        'test/hr_timesheet_report.yml',
        'test/hr_timesheet_demo.yml',
    ],
    'installable': True,
    'auto_install': False,
    'certificate': '0071405533469',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
