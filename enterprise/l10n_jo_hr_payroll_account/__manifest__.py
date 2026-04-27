# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Jordan - Payroll with Accounting',
    'countries': ['jo'],
    'version': '1.0',
    'category': 'Human Resources',
    'description': """
Accounting Data for Jordan Payroll Rules
========================================
    """,
    'depends': ['hr_payroll_account', 'l10n_jo', 'l10n_jo_hr_payroll'],
    'data': [
        'data/account_chart_template_data.xml',
    ],
    'demo': [
        'data/l10n_jo_hr_payroll_account_demo.xml',
    ],
    'license': 'OEEL-1',
    'auto_install': True,
}
