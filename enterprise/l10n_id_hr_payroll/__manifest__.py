# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Indonesia - Payroll',
    'countries': ['id'],
    'category': 'Human Resources/Payroll',
    'description': """
        Indonesia Payroll Rules.
    """,
    'depends': [
        'hr_payroll',
        'hr_contract_reports',
        'hr_work_entry_holidays',
        'hr_payroll_holidays',
    ],
    'auto_install': ['hr_payroll'],
    'data': [
        "data/resource_calendar_data.xml",
        "data/hr_work_entry_type_data.xml",
        "data/hr_leave_type_data.xml",
        "data/hr_payroll_structure_type_data.xml",
        "data/hr_payroll_structure_data.xml",
        "data/hr_payslip_input_type_data.xml",
        "data/hr_salary_rule_category_data.xml",
        "data/hr_rule_parameter_data.xml",
        "data/hr_salary_rule_data.xml",
        "views/hr_employee_views.xml",
        "views/hr_contract_views.xml",
        "views/res_config_settings_views.xml",
        "views/hr_payslip_views.xml",
        "views/hr_payslip_line_views.xml",
    ],
    'demo': [
        "data/l10n_id_hr_payroll_demo.xml"
    ],
    'license': 'OEEL-1',
}
