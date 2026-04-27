# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Australia - Payroll with Accounting',
    'category': 'Human Resources',
    'depends': [
        'l10n_au_hr_payroll',
        'hr_payroll_account',
        'l10n_au',
        "l10n_au_aba"
    ],
    'description': """
Accounting Data for Australian Payroll Rules.
=============================================
    """,

    'auto_install': True,
    'data': [
        "data/hr_salary_rules.xml",
        "data/account_chart_template_data.xml",
        "data/ir_sequence_data.xml",
        "data/res_partner.xml",
        "data/hr_payroll_dashboard_warning_data.xml",
        "data/mail_activity_type_data.xml",
        "data/l10n_au_payslip_ytd.xml",
        "views/l10n_au_super_stream_views.xml",
        "views/l10n_au_super_fund_views.xml",
        "views/hr_contract_views.xml",
        "views/hr_payslip_views.xml",
        "views/res_config_settings_views.xml",
        "views/hr_payslip_run_views.xml",
        "views/hr_employee_views.xml",
        "views/l10n_au_stp_views.xml",
        "views/l10n_au_payevnt_0004_template.xml",
        "views/l10n_au_payslip_ytd_views.xml",
        "views/account_move_views.xml",
        "wizard/account_payment_register_views.xml",
        "wizard/hr_payroll_report_wizard_views.xml",
        "wizard/l10n_au_stp_submit.xml",
        "wizard/l10n_au_previous_payroll_transfer_views.xml",
        "wizard/l10n_au_payroll_finalisation_views.xml",
        "wizard/l10n_au_stp_ffr_views.xml",
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
    ],
    'demo': [
        "data/l10n_au_hr_payroll_account_demo.xml",
    ],
    'license': 'OEEL-1',
}
