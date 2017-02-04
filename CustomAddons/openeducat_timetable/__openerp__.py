# -*- coding: utf-8 -*-
###############################################################################
#
#    Tech-Receptives Solutions Pvt. Ltd.
#    Copyright (C) 2009-TODAY Tech-Receptives(<http://www.techreceptives.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

{
    'name': 'KHF_Extension OpenEduCat Timetable',
    'version': '2.4.0',
    'category': 'Openerp Education',
    "sequence": 3,
    'summary': 'Manage TimeTables',
    'complexity': "easy",
    'description': """
        Egzaminų ir tvarkaraščio valdymo modulis

    """,
    'author': 'Tech Receptives, Evaldas Grišius ',
    'website': 'http://www.openeducat.org',
    'depends': ['openeducat_core', 'openeducat_classroom'],
    'data': [
        'views/timetable_view.xml',
        'views/period_view.xml',
        'views/faculty_view.xml',
        'views/exam_view.xml',
        'report/report_timetable_student_generate.xml',
        'report/report_timetable_teacher_generate.xml',
        'report/report_menu.xml',
        'wizard/generate_timetable_view.xml',
        'wizard/time_table_report.xml',
        'dashboard/timetable_student_dashboard.xml',
        'dashboard/timetable_faculty_dashboard.xml',
        'security/ir.model.access.csv',
        'timetable_menu.xml',
    ],
    'demo': [
        'demo/op.period.csv',
        'demo/op_timetable_demo.xml'
    ],
    'images': [
        'static/description/openeducat_timetable_banner.jpg',
        'static/img/logo.png'
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    
}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
