# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Bangladesh - Payroll',
    'countries': ['bd'],
    'category': 'Human Resources/Payroll',
    'description': """
Bangladesh Payroll Rules.
=========================
- Salary rules calculation
- Income tax credits handling
- Introduced the income tax slabs calculations
    """,
    'depends': ['hr_payroll'],
    'auto_install': ['hr_payroll'],
    'data': [
        'data/hr_rule_parameters_data.xml',
        'data/hr_payroll_structure_type_data.xml',
        'data/hr_payroll_structure_data.xml',
        'data/hr_salary_rule_category_data.xml',
        'data/hr_payslip_input_type_data.xml',
        'data/hr_salary_rule_data.xml',
        'views/hr_employee_views.xml',
    ],
    'license': 'OEEL-1',
}
