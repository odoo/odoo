#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
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
