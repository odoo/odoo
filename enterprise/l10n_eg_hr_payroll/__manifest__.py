# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Egypt - Payroll",
    "countries": ["eg"],
    "category": "Human Resources/Payroll",
    "description": """
Egypt Payroll and End of Service rules.
=======================================
- Basic calculation
- End of service calculation
- Other inputs (overtime, salary attachments, etc.)
- Social insurance calculation
- End of service provisions
- Tax break calculations and deductions
- Master payroll export
    """,
    "depends": ["hr_payroll"],
    "auto_install": ["hr_payroll"],
    "data": [
        "security/ir.model.access.csv",
        "data/hr_rule_parameter_data.xml",
        "data/hr_salary_rule_category_data.xml",
        "data/hr_payroll_structure_type_data.xml",
        "data/hr_payroll_structure_data.xml",
        "data/hr_salary_rule_data.xml",
        "views/hr_contract_views.xml",
        "views/hr_payroll_master_report_views.xml",
    ],
    "license": "OEEL-1",
}
