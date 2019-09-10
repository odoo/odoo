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
    'name': 'Belgium - Payroll with Accounting',
    'category': 'Localization',
    'author': 'OpenERP SA',
    'depends': ['l10n_be_hr_payroll', 'hr_payroll_account', 'l10n_be'],
    'version': '1.0',
    'description': """
Accounting Data for Belgian Payroll Rules.
==========================================
    """,

    'auto_install': True,
    'website': 'https://www.odoo.com/page/accounting',
    'demo': [],
    'data':[
        'l10n_be_wizard.yml',
        'l10n_be_hr_payroll_account_data.xml',
        'data/hr.salary.rule.csv',
    ],
    'installable': True
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
