# -*- encoding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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
    'name': 'hr_payroll_l10n_be',
    'category': 'payroll',
    'init_xml':[],
    'author': 'AOS',
    'depends': ['hr_payroll','hr_contract'],
    'version': '1.0',
    'description': """
Belgian Payroll system.
=======================

    * Employee Details
    * Employee Contracts
    * Passport based Contract
    * Allowances / Deductions
    * Allow to configure Basic / Grows / Net Salary
    * Employee Payslip
    * Monthly Payroll Register
    * Integrated with Holiday Management
    * Salary Maj, ONSS, Precompte Professionnel, Child Allowance, ...
    """,

    'active': False,
    'demo_xml': [],
    'update_xml':[
	 'hr_payroll_l10n_be_view.xml',
	 'hr_payroll_l10n_be_data.xml',
	 'data/hr.salary.rule.csv',
    ],
    'installable': True
}
