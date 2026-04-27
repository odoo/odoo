# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'United States - Payroll - State Calculation',
    'countries': ['us'],
    'category': 'Human Resources/Payroll',
    'depends': ['l10n_us_hr_payroll'],
    'version': '1.0',
    'description': 'Add fields for state calculation of payroll on the employee.',
    'data': [
        'data/hr_salary_rule_data.xml',
        'views/hr_employee.xml',
    ],
    'license': 'OEEL-1',
    'auto_install': True,
}
