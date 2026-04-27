# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Indonesia - Payroll with Accounting',
    'author': 'Odoo',
    'version': '1.0',
    'category': 'Human Resources',
    'description': """
Accounting Data for Indonesian Payroll Rules
============================================
    """,
    'depends': ['hr_payroll_account', 'l10n_id', 'l10n_id_hr_payroll'],
    'data': [
        'data/account_chart_template_data.xml',
    ],
    'demo': [
        'data/l10n_id_hr_payroll_account_demo.xml',
    ],
    'license': 'OEEL-1',
    'auto_install': True,
}
