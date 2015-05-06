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
    'name': 'Payroll Accounting',
    'version': '1.0',
    'category': 'Human Resources',
    'description': """
Generic Payroll system Integrated with Accounting.
==================================================

    * Expense Encoding
    * Payment Encoding
    * Company Contribution Management
    """,
    'author':'OpenERP SA',
    'website': 'https://www.odoo.com/page/employees',
    'depends': [
        'hr_payroll',
        'account',
        'hr_expense'
    ],
    'data': ['hr_payroll_account_view.xml'],
    'demo': ['hr_payroll_account_demo.xml'],
    'test': ['../account/test/account_minimal_test.xml', 'test/hr_payroll_account.yml'],
    'installable': True,
    'auto_install': False,
}
