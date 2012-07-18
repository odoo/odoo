# -*- encoding: utf-8 -*-
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
    'name': 'Indian Payroll',
    'category': 'Localization',
    'init_xml': [],
    'author': 'OpenERP SA',
    'website':'http://www.openerp.com',
    'depends': ['hr_payroll'],
    'version': '1.0',
    'description': """
Indian Payroll Salary Rules.
=======================

    -Configuration of hr_payroll for India localization
    -All main contributions rules for India payslip.
    * New payslip report
    * Employee Contracts
    * Allow to configure Basic / Gross / Net Salary
    * Employee PaySlip
    * Allowance / Deduction
    * Integrated with Holiday Management
    * Medical Allowance, Travel Allowance, Child Allowance, ...
    - Payroll Advice and Report
    """,

    'active': False,
    'update_xml': [
         'l10n_in_hr_payroll_view.xml',
         'data/l10n_in_hr_payroll_data.xml',
         'data/hr.salary.rule.csv',
         'security/ir.model.access.csv',
         'l10n_in_hr_payroll_report.xml',
         'l10n_in_hr_payroll_sequence.xml',
         'wizard/salary_rule_bymonth.xml'
     ],
    'demo_xml': ['l10n_in_hr_payroll_demo.xml'],
    'installable': True
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
