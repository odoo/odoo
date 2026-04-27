# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'United Arab Emirates - Payroll with Accounting',
    'category': 'Human Resources',
    'description': """
Accounting Data for UAE Payroll Rules.
=======================================================

    """,
    'depends': ['hr_payroll_account', 'l10n_ae', 'l10n_ae_hr_payroll'],
    'data': [
        'data/account_chart_template_data.xml',
        'data/res_bank_data.xml',
    ],
    'demo': [
        'data/l10n_ae_hr_payroll_account_demo.xml',
    ],
    'license': 'OEEL-1',
    'auto_install': True,
}
