# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Switzerland - Payroll',
    'icon': '/account/static/description/l10n.png',
    'countries': ['ch'],
    'category': 'Human Resources/Payroll',
    'depends': ['hr_payroll', 'hr_contract_reports', 'hr_work_entry_holidays', 'hr_payroll_holidays'],
    'auto_install': ['hr_payroll'],
    'version': '1.0',
    'description': """
Switzerland Payroll Rules.
==========================

    * Employee Details
    * Employee Contracts
    * Passport based Contract
    * Allowances/Deductions
    * Allow to configure Basic/Gross/Net Salary
    * Employee Payslip
    * Integrated with Leaves Management
    * Compute payslips according to ELM 5 standard
    """,
    'data': [
        'data/hr_salary_rule_category_data.xml',
        'data/hr_payroll_structure_type_data.xml',
        'data/report_paperformat_data.xml',
        'data/hr_work_entry_type_data.xml',
        'views/hr_payroll_report.xml',
        'data/hr_payroll_structure_data.xml',
        'data/hr_rule_parameters_data.xml',
        'data/hr_payslip_input_type_data.xml',
        'data/hr_salary_rule_data.xml',
        'data/hr_contract_type_data.xml',
        'views/res_users_views.xml',
        'views/hr_employee_views.xml',
        'views/res_config_settings_views.xml',
        'views/report_payslip_templates.xml',
        'views/l10n_ch_location_unit_views.xml',
        'views/l10n_ch_hr_employee_children_views.xml',
        'views/hr_contract_views.xml',
        'views/hr_salary_rule_views.xml',
        'views/l10n_ch_individual_account_views.xml',
        'views/l10n_ch_monthly_summary_views.xml',
        'views/l10n_ch_social_insurance_views.xml',
        'views/l10n_ch_lpp_insurance_views.xml',
        'views/l10n_ch_accident_insurance_views.xml',
        'views/l10n_ch_additional_accident_insurance_views.xml',
        'views/l10n_ch_sickness_insurance_views.xml',
        'views/l10n_ch_compensation_fund_views.xml',
        'views/l10n_ch_employee_is_line.xml',
        'views/l10n_ch_hr_payroll_insurance_report_pdf.xml',
        'views/l10n_ch_hr_payroll_salary_certificate.xml',
        'views/l10n_ch_insurance_report_views.xml',
        'views/l10n_ch_salary_certificate_report_views.xml',
        'views/l10n_ch_tax_at_source_report_views.xml',
        'views/hr_payslip_views.xml',
        'views/hr_payslip_run_views.xml',
        'wizard/l10n_ch_tax_rate_import_views.xml',
        'wizard/l10n_ch_hr_payroll_employee_lang_views.xml',
        'report/l10n_ch_monthly_summary_template.xml',
        'report/l10n_ch_individual_account_template.xml',
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/menuitems.xml',
    ],
    'demo': [
        'data/l10n_ch_hr_payroll_demo.xml',
    ],
    'license': 'OEEL-1',
}
