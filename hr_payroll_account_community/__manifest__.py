# -*- coding: utf-8 -*-
###################################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2022-TODAY Cybrosys Technologies (<https://www.cybrosys.com>).
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
###################################################################################

{
    'name': 'Odoo16 Payroll Accounting',
    'category': 'Generic Modules/Human Resources',
    'live_test_url': 'https://www.youtube.com/watch?v=Ykni1o8VBlc&feature=youtu.be',
    'summary': """
          Generic Payroll system Integrated with Accounting,Expense Encoding,Payment Encoding,Company Contribution Management
    """,
    'description': """Odoo16 Payroll Accounting,Odoo15 Payroll,Odoo 15,Payroll Accounting,Accounting""",
    'version': '16.0.1.0.0',
    'author': 'Odoo SA,Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'depends': ['hr_payroll_community', 'account'],
    'images': ['static/description/banner.png'],
    'data': ['views/hr_payroll_account_views.xml'],
    'test': ['../account/test/account_minimal_test.xml'],
    'demo': ['data/hr_payroll_account_demo.xml'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
