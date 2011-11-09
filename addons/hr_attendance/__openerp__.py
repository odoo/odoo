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
    'name': 'Attendance',
    'version': '1.1',
    'category': 'Human Resources',
    'complexity': "easy",
    'description': """
This module aims to manage employee's attendances.
==================================================

Keeps account of the attendances of the employees on the basis of the
actions(Sign in/Sign out) performed by them.
       """,
    'author': 'OpenERP SA',
    'images': ['images/hr_attendances.jpeg'],
    'depends': ['hr'],
    'update_xml': [
        'security/ir.model.access.csv',
        'hr_attendance_view.xml',
        'hr_attendance_report.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'wizard/hr_attendance_bymonth_view.xml',
        'wizard/hr_attendance_byweek_view.xml',
        'wizard/hr_attendance_error_view.xml',
        'wizard/hr_attendance_sign_in_out_view.xml',
    ],
    'demo_xml': ['hr_attendance_demo.xml'],
    'test': ['test/test_hr_attendance.yml',
             'test/hr_attendance_report.yml'
    ],
    'installable': True,
    'active': False,
    'certificate': '0063495605613',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
