# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Australia - Payroll",
    "category": "Human Resources/Payroll",
    "countries": ["au"],
    "depends": [
        "hr_payroll",
        "hr_contract_reports",
        "hr_work_entry_holidays",
        "hr_payroll_holidays",
    ],
    "description": """
Australian Payroll Rules.
=========================
""",
    "data": [
        "security/ir.model.access.csv",
        "views/hr_contract_views.xml",
        "views/hr_employee_views.xml",
        "views/res_config_settings_views.xml",
        "views/hr_payroll_report.xml",
        "views/hr_payslip_views.xml",
        "views/hr_structure_type_views.xml",
        "views/hr_payslip_input_type_views.xml",
        "views/hr_leave_type_views.xml",
        "views/hr_payslip_run_views.xml",
        "views/hr_work_entry_type_views.xml",
        "views/report_payslip_templates.xml",
        "views/l10n_au_payevnt_0004_views.xml",
        "views/l10n_au_payevnt_0004_template.xml",
        "views/l10n_au_super_fund_views.xml",
        "views/l10n_au_super_account_views.xml",
        "views/ir_ui_menu.xml",
        "data/ir_sequence_data.xml",
        "data/resource_calendar_data.xml",
        "data/hr_salary_rule_category_data.xml",
        "data/hr_payroll_structure_type_data.xml",
        "data/hr_payslip_input_type_data.xml",
        "data/hr_payroll_structure_data.xml",
        "data/hr_rule_parameters_data.xml",
        "data/salary_rules/hr_salary_rule_actor_data.xml",
        "data/salary_rules/hr_salary_rule_actor_promotional_data.xml",
        "data/salary_rules/hr_salary_rule_horticulture_data.xml",
        "data/salary_rules/hr_salary_rule_lumpsum_data.xml",
        "data/salary_rules/hr_salary_rule_no_tfn_data.xml",
        "data/salary_rules/hr_salary_rule_regular_data.xml",
        "data/salary_rules/hr_salary_rule_return_to_work_data.xml",
        "data/salary_rules/hr_salary_rule_termination_data.xml",
        "data/salary_rules/hr_salary_rule_whm_data.xml",
        "data/hr_work_entry_type_data.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "l10n_au_hr_payroll/static/src/js/**/*",
        ],
    },
    "demo": [
        "data/l10n_au_hr_payroll_demo.xml",
    ],
    "license": "OEEL-1",
}
