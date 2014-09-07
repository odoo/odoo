#-*- coding:utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    d$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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
    'name': 'Payroll',
    'version': '1.0',
    'category': 'Human Resources',
    'sequence': 38,
    'description': """
Generic Payroll system.
=======================

    * Employee Details
    * Employee Contracts
    * Passport based Contract
    * Allowances/Deductions
    * Allow to configure Basic/Gross/Net Salary
    * Employee Payslip
    * Monthly Payroll Register
    * Integrated with Holiday Management
    """,
    'author': 'OpenERP SA',
    'website': 'https://www.odoo.com/page/employees',
    'images': [
        'images/hr_company_contributions.jpeg',
        'images/hr_salary_heads.jpeg',
        'images/hr_salary_structure.jpeg',
        'images/hr_employee_payslip.jpeg'
    ],
    'depends': [
        'hr',
        'hr_contract',
        'hr_holidays',
        'decimal_precision',
        'report',
    ],
    'data': [
        'security/hr_security.xml',
        'wizard/hr_payroll_payslips_by_employees.xml',
        'hr_payroll_view.xml',
        'hr_payroll_workflow.xml',
        'hr_payroll_sequence.xml',
        'hr_payroll_report.xml',
        'hr_payroll_data.xml',
        'security/ir.model.access.csv',
        'wizard/hr_payroll_contribution_register_report.xml',
        'res_config_view.xml',
        'views/report_contributionregister.xml',
        'views/report_payslip.xml',
        'views/report_payslipdetails.xml',
    ],
    'test': [
        'test/payslip.yml',
    ],
    'demo': ['hr_payroll_demo.xml'],
    'installable': True,
    'auto_install': False,
    'application': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
