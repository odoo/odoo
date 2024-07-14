# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Morocco - Payroll with Accounting',
    'countries': ['ma'],
    'category': 'Human Resources',
    'depends': ['l10n_ma_hr_payroll', 'hr_payroll_account', 'l10n_ma'],
    'description': """
Accounting Data for Moroccan Payroll Rules.
=================================================
    """,

    'auto_install': True,
    'demo': [
        'data/l10n_ma_hr_payroll_account_demo.xml',
    ],
    'license': 'OEEL-1',
}
