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
    'name': 'French Payroll',
    'category': 'Localization/Payroll',
    'author': 'Yannick Buron (SYNERPGY)',
    'depends': ['hr_payroll', 'l10n_fr'],
    'version': '1.0',
    'description': """
French Payroll Rules.
=====================

    - Configuration of hr_payroll for French localization
    - All main contributions rules for French payslip, for 'cadre' and 'non-cadre'
    - New payslip report

TODO :
------
    - Integration with holidays module for deduction and allowance
    - Integration with hr_payroll_account for the automatic account_move_line
      creation from the payslip
    - Continue to integrate the contribution. Only the main contribution are
      currently implemented
    - Remake the report under webkit
    - The payslip.line with appears_in_payslip = False should appears in the
      payslip interface, but not in the payslip report
    """,

    'active': False,
    'update_xml':[
     'l10n_fr_hr_payroll_view.xml',
     'l10n_fr_hr_payroll_data.xml',
    ],
    'installable': True
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
