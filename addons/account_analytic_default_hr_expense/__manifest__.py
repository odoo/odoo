# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Account Analytic Defaults for expenses.',
    'version': '1.0',
    'category': 'Accounting',
    'description': """
Set default values for your analytic accounts on your hr expenses.
==================================================================

Allows to automatically select analytic accounts based on Product
    """,
    'depends': ['account_analytic_default', 'hr_expense'],
    'auto_install': True,
}
