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
    'name': 'Human Resource Payroll',
    'version': '1.0',
    'category': 'Human Resources',
    'description': """
Generic Payroll system.
=======================

    * Employee Details
    * Employee Contracts
    * Passport based Contract
    * Allowances / Deductions
    * Allow to configure Basic / Grows / Net Salary
    * Employee Payslip
    * Monthly Payroll Register
    * Integrated with Holiday Management
    """,
    'author':'OpenERP SA',
    'website':'http://www.openerp.com',
    'images': ['images/hr_company_contributions.jpeg','images/hr_salary_heads.jpeg','images/hr_salary_structure.jpeg','images/hr_employee_payslip.jpeg','images/hr_payment_advice.jpeg','images/hr_payroll_register.jpeg'],
    'depends': [
        'hr',
        'hr_contract',
        'hr_holidays',
        'decimal_precision',
    ],
    'init_xml': [
    ],
    'update_xml': [
        'security/hr_security.xml',
        'hr_payroll_view.xml',
        'hr_payroll_workflow.xml',
        'hr_payroll_sequence.xml',
        'hr_payroll_report.xml',
        'hr_payroll_data.xml',
        'security/ir.model.access.csv',
        'wizard/hr_payroll_employees_detail.xml',
        'wizard/hr_payroll_year_salary.xml',
    ],
    'test': [
#         'test/payslip.yml',
#         'test/payment_advice.yml',
#         'test/payroll_register.yml',
        # 'test/hr_payroll_report.yml',
    ],
    'demo_xml': [
        'hr_payroll_demo.xml'
    ],
    'installable': True,
    'active': False,
    'certificate' : '001046261404562128861',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
