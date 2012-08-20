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
    'name': 'Contracts Management: hr_expense link',
    'version': '1.1',
    'category': 'Hidden',
    'description': """
This module is for modifying account analytic view to show some data related to the hr_expense module.

""",
    'author': 'OpenERP S.A.',
    'website': 'http://www.openerp.com/',
    'depends': ['hr_expense','account_analytic_analysis'],
    'data': [
                    'analytic_contract_hr_expense_view.xml',
                    ],
    'demo': [],
    'css' : [
             ],
    'installable': True,
    'auto_install': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
