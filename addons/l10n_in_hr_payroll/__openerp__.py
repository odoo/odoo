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
    'name': 'India payroll',
    'category': 'Localization',
    'init_xml': [],
    'author': 'OpenERP SA',
    'website':'http://www.openerp.com',
    'depends': ['hr_payroll'],
    'version': '1.0',
    'description': """
Indian Payroll Rules.
=======================

    -Configuration of hr_payroll for India localization
    -All main contributions rules for India payslip.
    * New payslip report
    * Employee Contracts
    * Allow to configure Basic / Grows / Net Salary
    * Employee PaySlip
    * Allowance / Deduction
    * Monthly Payroll Register
    * Integrated with Holiday Management
    * Medical Allowance, Travel Allowance, Child Allowance, ...
    """,

    'active': False,
    'update_xml': [
         'l10n_in_hr_payroll_view.xml',
         'l10n_in_hr_payroll_data.xml',
         'data/hr.salary.rule.csv',
         'l10n_in_hr_payroll_report.xml',
     ],
    'demo_xml': ['l10n_in_hr_payroll_demo.xml'],
    'installable': True
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: