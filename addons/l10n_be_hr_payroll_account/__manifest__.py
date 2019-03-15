# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Belgium - Payroll with Accounting',
    'category': 'Human Resources',
    'depends': ['l10n_be_hr_payroll', 'hr_payroll_account'],
    'description': """
Accounting Data for Belgian Payroll Rules.
==========================================
    """,

    'auto_install': True,
    'data':[],
    'demo':['data/l10n_be_hr_payroll_account_demo.xml'],
    'post_init_hook': '_set_accounts',
}
