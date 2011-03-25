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
    "name": "Human Resources: Holidays management",
    "version": "1.5",
    "author": ['OpenERP SA', 'Axelor'],
    "category": "Human Resources",
    "website": "http://www.openerp.com",
    "description": """
This module allows you to manage leaves and leaves' requests.
=============================================================

Implements a dashboard for human resource management that includes.
    * Leaves

Note that:
    - A synchronisation with an internal agenda (use of the CRM module) is possible: in order to automatically create a case when an holiday request is accepted, you have to link the holidays status to a case section. You can set up this info and your colour preferences in
                Human Resources/Configuration/Holidays/Leave Type
    - An employee can make an ask for more off-days by making a new Allocation It will increase his total of that leave type available (if the request is accepted).
    - There are two ways to print the employee's holidays:
        * The first will allow to choose employees by department and is used by clicking the menu item located in
                Human Resources/Reporting/Holidays/Leaves by Department
        * The second will allow you to choose the holidays report for specific employees. Go on the list
                Human Resources/Human Resources/Employees
                then select the ones you want to choose, click on the print icon and select the option
                'Employee's Holidays'
    - The wizard allows you to choose if you want to print either the Confirmed & Validated holidays or only the Validated ones. These states must be set up by a user from the group 'HR'. You can define these features in the security tab from the user data in
                Administration / Users / Users
                for example, you maybe will do it for the user 'admin'.
""",
    'images': ['images/hr_allocation_requests.jpeg', 'images/hr_leave_requests.jpeg', 'images/leaves_analysis.jpeg'],
    'depends': ['hr', 'crm', 'process', 'resource'],
    'init_xml': [],
    'update_xml': [
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'hr_holidays_workflow.xml',
        'hr_holidays_view.xml',
        'hr_holidays_data.xml',
        'hr_holidays_wizard.xml',
        'hr_holidays_report.xml',
        'report/hr_holidays_report_view.xml',
        'report/available_holidays_view.xml',
        'wizard/hr_holidays_summary_department_view.xml',
        'wizard/hr_holidays_summary_employees_view.xml',
        'board_hr_holidays_view.xml',
        'board_hr_manager_holidays_view.xml',
        ],
    'demo_xml': ['hr_holidays_demo.xml',],
    'test': ['test/test_hr_holiday.yml',
             'test/hr_holidays_report.yml',
             ],
    'installable': True,
    'active': False,
    'certificate': '0086579209325',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
