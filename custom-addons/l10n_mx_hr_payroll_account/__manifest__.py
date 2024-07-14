# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Mexico - Payroll with Accounting',
    'countries': ['mx'],
    'author': 'Odoo',
    'version': '1.0',
    'category': 'Human Resources',
    'description': """
Accounting Data for Mexico Payroll Rules
============================================
    """,
    'depends': ['hr_payroll_account', 'l10n_mx', 'l10n_mx_hr_payroll', 'l10n_mx_edi'],
    'data': [
        'data/l10n_mx_hr_payroll_account_data.xml',
    ],
    'demo': [
        'data/l10n_mx_hr_payroll_account_demo.xml',
    ],
    'license': 'OEEL-1',
    'auto_install': True,
}
