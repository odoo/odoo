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
    'name': 'Leave Management',
    'version': '1.5',
    'author': 'OpenERP SA',
    'category': 'Human Resources',
    'sequence': 28,
    'summary': 'Holidays, Allocation and Leave Requests',
    'website': 'http://www.openerp.com',
    'description': """
Manage leaves and allocation requests
=====================================
This application controls the holiday's schedule of your company. It allow employees to request holidays. Then, managers can review requests for holiday and approve or reject. This way you can control the overall holiday's planning for the company or departement.

You can configure all kinds of leaves (sickness, holidays, paid days, ...) and allocate leaves to employee or departement quickly using allocation requests. An employee can also make an ask for more off-days by making a new Allocation. It will increase his total of that leave type available (if the request is accepted).

You can keep record of leaves different ways by following reports: 

* Leaves Summary
* Leaves by Department
* Leaves Analysis

A synchronisation with an internal agenda (meeting of the CRM module) is also possible: in order to automatically create a meeting when an holiday request is accepted by setting up in type of meeting in Leave Type.
""",
    'images': ['images/hr_allocation_requests.jpeg', 'images/hr_leave_requests.jpeg', 'images/leaves_analysis.jpeg'],
    'depends': ['hr', 'base_calendar', 'process', 'resource'],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'hr_holidays_workflow.xml',
        'hr_holidays_view.xml',
        'hr_holidays_data.xml',
        'hr_holidays_report.xml',
        'report/hr_holidays_report_view.xml',
        'report/available_holidays_view.xml',
        'wizard/hr_holidays_summary_department_view.xml',
        'wizard/hr_holidays_summary_employees_view.xml',
        'board_hr_holidays_view.xml',
        ],
    'demo': ['hr_holidays_demo.xml',],
    'test': ['test/test_hr_holiday.yml',
             'test/hr_holidays_report.yml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'certificate': '0086579209325',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
