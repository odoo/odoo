# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 OpenERP SA (<http://openerp.com>).
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
    'name': 'Belgian Payroll Rules',
    'category': 'Localization/Payroll',
    'author': 'OpenERP SA',
    'depends': ['hr_payroll','hr_contract'],
    'version': '1.0',
    'description': """
Belgian Payroll Rules
=====================

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
    'demo': [
     'l10n_be_hr_payroll_demo.xml',
    ],
    'data':[
     'l10n_be_hr_payroll_view.xml',
     'l10n_be_hr_payroll_data.xml',
     'data/hr.salary.rule.csv',
    ],
    'installable': True
}
