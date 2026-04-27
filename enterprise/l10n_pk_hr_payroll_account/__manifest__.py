# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Pakistan - Payroll with Accounting',
    'version': '1.0',
    'category': 'Human Resources',
    'description': """
Accounting Data for Pakistan Payroll Rules
==========================================
    """,
    'depends': ['hr_payroll_account', 'l10n_pk', 'l10n_pk_hr_payroll'],
    'data': [
        'data/account_chart_template_data.xml',
    ],
    'demo': [
        'data/l10n_pk_hr_payroll_account_demo.xml',
    ],
    'license': 'OEEL-1',
    'auto_install': True,
}
