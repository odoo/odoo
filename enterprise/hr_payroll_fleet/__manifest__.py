# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Payroll - Fleet',
    'version': '1.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Integration between Payroll and Fleet.',
    'depends': ['hr_payroll', 'hr_fleet'],
    'auto_install': True,
    'data': [
        'data/hr_payroll_dashboard_warning_data.xml',
    ],
    'license': 'OEEL-1',
}
