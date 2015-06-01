# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Belgium - Payroll with Accounting',
    'category': 'Localization',
    'author': 'OpenERP SA',
    'depends': ['l10n_be_hr_payroll', 'hr_payroll_account', 'l10n_be'],
    'version': '1.0',
    'description': """
Accounting Data for Belgian Payroll Rules.
==========================================
    """,

    'auto_install': True,
    'website': 'https://www.odoo.com/page/accounting',
    'demo': [],
    'data':[
        'l10n_be_hr_payroll_account_data.xml',
        'data/hr.salary.rule.csv',
    ],
    'installable': False
}
