# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Hong Kong - Payroll',
    'countries': ['hk'],
    'category': 'Human Resources/Payroll',
    'depends': [
        'hr_payroll',
        'hr_contract_reports',
        'hr_work_entry_holidays',
        'hr_payroll_holidays',
    ],
    'version': '1.0',
    'description': """
Hong Kong Payroll Rules.
========================
    """,
    'data': [
        "security/ir.model.access.csv",
        "report/report_payslip.xml",
        "report/report_payslip_action.xml",
        "data/hr_work_entry_type_data.xml",
        "data/hr_departure_reason_data.xml",
        "data/resource_calendar_data.xml",
        "data/hr_payroll_structure_type_data.xml",
        "data/hr_payroll_structure_data.xml",
        "data/hr_payslip_input_type_data.xml",
        "data/hr_salary_rule_category_data.xml",
        "data/hr_rule_parameters_data.xml",
        "data/hr_leave_type_data.xml",
        "data/ir_cron_data.xml",
        'data/ir_default_data.xml',
        'data/ir_sequence_data.xml',
        "data/report_paperformat_data.xml",
        "data/cap57/employee_salary_data.xml",
        "data/cap57/employee_payment_in_lieu_of_notice_data.xml",
        "data/cap57/employee_long_service_payment_data.xml",
        "data/cap57/employee_severance_payment_data.xml",
        "views/hr_contract_views.xml",
        "views/hr_departure_reason_views.xml",
        "views/hr_employee_views.xml",
        "views/hr_payslip_run_views.xml",
        "views/hr_payslip_views.xml",
        "views/hr_work_entry_views.xml",
        "views/l10n_hk_manulife_mpf_views.xml",
        "views/l10n_hk_ir56b_views.xml",
        "views/l10n_hk_ir56e_views.xml",
        "views/l10n_hk_ir56f_views.xml",
        "views/l10n_hk_ir56g_views.xml",
        "views/l10n_hk_rental_views.xml",
        "views/reports.xml",
        "views/res_bank_views.xml",
        "views/res_config_settings_views.xml",
        "views/hr_payroll_employee_declaration_views.xml",
        "views/menuitems.xml",
        "report/ir56b_pdf_template.xml",
        "report/ir56b_xml_template.xml",
        "report/ir56e_pdf_template.xml",
        "report/ir56f_pdf_template.xml",
        "report/ir56f_xml_template.xml",
        "report/ir56g_pdf_template.xml",
        "wizards/hr_payroll_hsbc_autopay_wizard_views.xml",
    ],
    'demo': [
        'data/l10n_hk_hr_payroll_demo.xml',
    ],
    'assets': {
        'web.report_assets_common': [
            'l10n_hk_hr_payroll/static/src/scss/report_ird.scss',
        ]
    },
    'license': 'OEEL-1',
}
