# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Belgium - Payroll',
    'countries': ['be'],
    'category': 'Human Resources/Payroll',
    'depends': ['certificate', 'hr_payroll', 'hr_contract_reports', 'hr_work_entry_holidays', 'hr_payroll_holidays'],
    'auto_install': ['hr_payroll'],
    'version': '1.0',
    'description': """
Belgian Payroll Rules.
======================

    * Employee Details
    * Employee Contracts
    * Passport based Contract
    * Allowances/Deductions
    * Allow to configure Basic/Gross/Net Salary
    * Employee Payslip
    * Monthly Payroll Register
    * Integrated with Leaves Management
    * Salary Maj, ONSS, Withholding Tax, Child Allowance, ...

Automatic DmfA Signature
========================

Prerequisites:
--------------

- You need a Belgian Government Compliant Digital Certificate, delivered by Global
  Sign. See: https://shop.globalsign.com/en/belgian-government-services

- Generate certificate files from your SSL certificate (.pfx file) that are needed to create
  a technical user (.cer file) and to authenticate remotely to the ONSS (.pem) file. On a UNIX
  system, you may use the following commands:

  - PFX -> CRT: openssl pkcs12 -in my_cert.pfx -out my_cert.crt -nokeys -clcerts

  - CRT -> CER: openssl x509 -inform pem -in my_cert.crt -outform der -out my_cert.cer

  - PFX -> PEM: openssl pkcs12 -in my_cert.pfx -out my_cert.pem -nodes

  - PFX -> KEY: openssl pkcs12 -in my_cert.pfx -out my_cert.key -nocerts

- Before you can use the social security REST web service, you must create an account
  for yourself or for your client and configure the security. (The whole procedure is
  available at https://www.socialsecurity.be/site_fr/general/helpcentre/batch/sftp/previewstep.htm)

  - Create a technical user + Activate a SFTP channel: Your client must now create a technical user in the Access management
    online service. The follow this procedure: https://www.socialsecurity.be/site_fr/general/helpcentre/rest/documents/pdf/webservices_creer_le_canal_FR.pdf

  - Configure your SFTP client: https://www.socialsecurity.be/site_fr/general/helpcentre/batch/document/pdf/step6_sftp_F.pdf

  - At the end of the procedure, you should have received a "ONSS Expeditor Number", you may
    encode in in the payroll Settings, with the .pem file and the related password, if any.
    """,

    'data': [
        'security/ir.model.access.csv',
        'security/l10n_be_hr_payroll_security.xml',
        'data/report_paperformat.xml',
        'views/report_payslip_templates.xml',
        'views/reports.xml',
        'wizard/hr_payroll_employee_departure_notice_views.xml',
        'wizard/hr_payroll_employee_departure_holiday_attest_views.xml',
        'wizard/hr_payroll_generate_warrant_payslips_views.xml',
        'wizard/l10n_be_hr_payroll_schedule_change_wizard_views.xml',
        'wizard/hr_payroll_allocating_paid_time_off_views.xml',
        'wizard/l10n_be_december_slip_wizard_views.xml',
        'wizard/l10n_be_group_insurance_wizard_views.xml',
        'views/l10n_be_double_pay_recovery_line_views.xml',
        'views/l10n_be_meal_voucher_report_views.xml',
        'views/hr_contract_views.xml',
        'views/hr_employee_views.xml',
        'views/res_users_views.xml',
        'views/hr_work_entry_views.xml',
        'views/report_termination_fees.xml',
        'views/report_termination_holidays.xml',
        'views/hr_dmfa_template.xml',
        'views/hr_dmfa_views.xml',
        'views/hr_departure_reason_views.xml',
        'views/273S_xml_export_template.xml',
        'views/281_10_xml_export_template.xml',
        'views/281_45_xml_export_template.xml',
        'views/withholding_tax_xml_export_template.xml',
        'views/hr_job_views.xml',
        'views/hr_leave_views.xml',
        'data/res_partner_data.xml',
        'data/contract_type_data.xml',
        'data/ir_default_data.xml',
        'data/resource_calendar_data.xml',
        'data/hr_work_entry_type_data.xml',
        'data/hr_leave_type_data.xml',
        'data/hr_payroll_dashboard_warning_data.xml',
        'data/hr_payroll_structure_type_data.xml',
        'data/hr_payroll_structure_data.xml',
        'data/hr_payslip_input_type_data.xml',
        'data/hr_salary_rule_category_data.xml',
        'data/hr_rule_parameters_data.xml',
        'data/ir_config_parameter_data.xml',
        'data/hr_departure_reason_data.xml',
        'data/cp200/employee_double_holidays_data.xml',
        'data/cp200/employee_pfi_data.xml',
        'data/cp200/employee_salary_data.xml',
        'data/cp200/employee_termination_fees_data.xml',
        'data/cp200/employee_termination_holidays_N1_data.xml',
        'data/cp200/employee_termination_holidays_N_data.xml',
        'data/cp200/employee_thirteen_month_data.xml',
        'data/cp200/employee_warrant_salary_data.xml',
        'data/cp200/employee_reimbursement_data.xml',
        'data/cp200/employee_cct90_data.xml',
        'data/student/student_regular_pay_data.xml',
        'data/ir_cron_data.xml',
        'views/res_config_settings_views.xml',
        'views/l10n_be_individual_account_views.xml',
        'views/l10n_be_281_10_views.xml',
        'views/l10n_be_281_45_views.xml',
        'report/hr_individual_account_templates.xml',
        'report/hr_contract_employee_report_views.xml',
        'report/hr_281_10_templates.xml',
        'report/hr_281_45_templates.xml',
        'report/hr_contract_history_report_views.xml',
        'report/l10n_be_hr_payroll_274_XX_sheet_template.xml',
        'report/l10n_be_hr_payroll_273S_pdf_template.xml',
        'report/hr_payroll_report_views.xml',
        'wizard/l10n_be_social_balance_sheet_views.xml',
        'report/l10n_be_social_balance_report_template.xml',
        'wizard/l10n_be_social_security_certificate_views.xml',
        'report/l10n_be_social_security_certificate_report_template.xml',
        'views/l10n_be_273S_views.xml',
        'views/l10n_be_274_XX_views.xml',
        'wizard/l10n_be_eco_vouchers_wizard_views.xml',
        'wizard/l10n_be_double_pay_recovery_wizard_views.xml',
        'wizard/l10n_be_hr_payroll_employee_lang_views.xml',
        'views/hr_payslip_views.xml',
        'views/hr_payslip_run_views.xml',
    ],
    'demo':[
        'data/l10n_be_hr_payroll_demo.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'l10n_be_hr_payroll/static/src/js/**/*',
        ],
        'web.report_assets_common': [
            'l10n_be_hr_payroll/static/src/scss/*.scss',
        ]
    },
    'license': 'OEEL-1',
}
