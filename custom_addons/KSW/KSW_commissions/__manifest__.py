{
    'name': 'KSW Commissions & Other Allowances',
    'version': '19.0.1.0.0',
    'summary': 'Monthly commission and allowance sheets for non-biometric '
               '(attendance-sheet) employees, with smart loan-shortfall '
               'recovery from KSW_deduction.',
    'description': """
Per-employee monthly Commissions & Other Allowances sheet for the
``x_is_attendance_sheet`` workforce. Supervisors fill in dynamic
allowance/commission lines from admin-managed categories; the sheet
automatically pulls any *deduction shortfall* from KSW_deduction
(installments the accountant reduced for a given month) and offers
it as a deductible from the bank-transfer total.

State machine:
  draft (supervisor edits) → confirmed (accountant reviews loans
  line) → done (sheet locked; manual paid line written back to
  KSW_deduction; pending shortfall reduced).

Phase A delivers the main sheet + KSW_deduction shortfall flow.
Phase B will add driver-commission sub-form, commission batches,
WPS / Kawthar bank-file export, and the PDF report.
""",
    'author': 'KSW',
    'category': 'Human Resources',
    'depends': [
        'hr',
        'mail',
        'KSW_working_schedule',
        'KSW_attendance_sheet',
        'KSW_deduction',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/category_data.xml',
        'data/ir_cron.xml',
        'views/ksw_commission_category_views.xml',
        'views/ksw_site_views.xml',
        'views/ksw_commission_template_views.xml',
        'reports/report_commission_sheet.xml',
        'reports/report_commissions_summary.xml',
        'reports/report_driver_commission_sheet.xml',
        'views/ksw_driver_commission_views.xml',
        'views/ksw_location_allowance_views.xml',
        'views/ksw_salesperson_profile_views.xml',
        'views/ksw_sales_commission_rule_views.xml',
        'views/ksw_sales_commission_sheet_views.xml',
        'wizard/sales_commission_override_wizard_views.xml',
        'wizard/sales_commission_import_wizard_views.xml',
        'views/ksw_commission_batch_views.xml',
        'views/ksw_commission_bank_export_wizard_views.xml',
        'views/hr_employee_views.xml',
        'views/res_partner_views.xml',
        'views/ksw_deduction_views.xml',
        'views/ksw_commission_sheet_views.xml',
        'views/res_config_settings_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}

