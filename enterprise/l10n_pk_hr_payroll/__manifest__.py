# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Pakistan - Payroll',
    'countries': ['pk'],
    'category': 'Human Resources/Payroll',
    'description': """
Pakistan Payroll and End of Service rules
=========================================
- Basic salaries calculations.
- Tax bracket calculations/deductions
    """,
    'depends': ['hr_payroll'],
    'auto_install': ['hr_payroll'],
    'data': [
        'data/hr_salary_rule_category_data.xml',
        'data/hr_payroll_structure_type_data.xml',
        'data/hr_payroll_structure_data.xml',
        'data/hr_salary_rule_data.xml',
        'data/hr_rule_parameter_data.xml',
    ],
    'license': 'OEEL-1',
}
