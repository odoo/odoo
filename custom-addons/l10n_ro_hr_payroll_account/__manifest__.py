# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Romania - Payroll with Accounting',
    'countries': ['ro'],
    'version': '1.0',
    'category': 'Human Resources/Payroll',
    'description': """
Accounting Data for Romania Payroll Rules
=========================================
    """,
    'depends': ['hr_payroll_account', 'l10n_ro', 'l10n_ro_hr_payroll'],
    'data': [
        'data/account_chart_template_data.xml',
    ],
    'demo': [
        'data/l10n_ro_hr_payroll_account_demo.xml',
    ],
    'license': 'OEEL-1',
    'auto_install': True,
}
