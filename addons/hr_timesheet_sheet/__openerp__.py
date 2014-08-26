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
    'sequence': 24,
    'summary': 'Timesheets, Attendances, Activities',
    'description': """
Record and validate timesheets and attendances easily
=====================================================

This application supplies a new screen enabling you to manage both attendances (Sign in/Sign out) and your work encoding (timesheet) by period. Timesheet entries are made by employees each day. At the end of the defined period, employees validate their sheet and the manager must then approve his team's entries. Periods are defined in the company forms and you can set them to run monthly or weekly.

The complete timesheet validation process is:
---------------------------------------------
* Draft sheet
* Confirmation at the end of the period by the employee
* Validation by the project manager

The validation can be configured in the company:
------------------------------------------------
* Period size (Day, Week, Month)
* Maximal difference between timesheet and attendances
    """,
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'images': ['images/hr_my_current_timesheet.jpeg','images/hr_timesheet_analysis.jpeg','images/hr_timesheet_sheet_analysis.jpeg','images/hr_timesheet_activity.jpeg'],
    'depends': ['hr_timesheet', 'hr_timesheet_invoice'],
    'data': [
        'security/ir.model.access.csv',
        'security/hr_timesheet_sheet_security.xml',
        'hr_timesheet_sheet_view.xml',
        'hr_timesheet_workflow.xml',
        'report/hr_timesheet_report_view.xml',
        'wizard/hr_timesheet_current_view.xml',
        'hr_timesheet_sheet_data.xml',
        'res_config_view.xml',
        'views/hr_timesheet_sheet.xml',
    ],
    'demo': ['hr_timesheet_sheet_demo.xml'],
    'test':['test/test_hr_timesheet_sheet.yml'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'qweb': ['static/src/xml/timesheet.xml',],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
