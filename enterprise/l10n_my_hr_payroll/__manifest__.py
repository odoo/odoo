# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Malaysia - Payroll',
    'countries': ['my'],
    'category': 'Human Resources/Payroll',
    'description': """
Malaysian Payroll and Tax Rules
===============================
- Social Security Premium/Insurance calculations for employment and unemployment
- Income tax calculations
- Stamp tax deductions
    """,
    'depends': ['hr_payroll'],
    'auto_install': ['hr_payroll'],
    'data': [
        'data/hr_rule_parameter_data.xml',
        'data/hr_salary_rule_category_data.xml',
        'data/hr_payroll_structure_type_data.xml',
        'data/hr_payroll_structure_data.xml',
        'data/hr_payslip_input_type_data.xml',
        'data/hr_salary_rule_data.xml',
        'views/hr_employee_views.xml',
    ],
    'license': 'OEEL-1',
    'demo':[
        'data/l10n_my_hr_payroll_demo.xml'
    ]
}
