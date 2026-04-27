# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Belgium - Payroll with Accounting',
    'category': 'Human Resources',
    'depends': ['l10n_be_hr_payroll', 'hr_payroll_account', 'l10n_be'],
    'description': """
Accounting Data for Belgian Payroll Rules.
==========================================
    """,

    'auto_install': True,
    'data':[
        'views/res_config_settings_views.xml',
        'views/l10n_be_274_XX_views.xml',
        'data/l10n_be_hr_payroll_account_data.xml',
    ],
    'license': 'OEEL-1',
}
