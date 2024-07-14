# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Accounting Reports',
    'summary': 'View and create reports',
    'category': 'Accounting/Accounting',
    'description': """
Accounting Reports
==================
    """,
    'depends': ['account_accountant'],
    'data': [
        'security/ir.model.access.csv',
        'data/pdf_export_templates.xml',
        'data/balance_sheet.xml',
        'data/cash_flow_report.xml',
        'data/executive_summary.xml',
        'data/profit_and_loss.xml',
        'data/bank_reconciliation_report.xml',
        'data/aged_partner_balance.xml',
        'data/general_ledger.xml',
        'data/trial_balance.xml',
        'data/sales_report.xml',
        'data/partner_ledger.xml',
        'data/multicurrency_revaluation_report.xml',
        'data/deferred_reports.xml',
        'data/journal_report.xml',
        'data/generic_tax_report.xml',
        'views/account_report_view.xml',
        'data/account_report_actions.xml',
        'data/menuitems.xml',
        'data/mail_activity_type_data.xml',
        'views/account_move_views.xml',
        'views/res_company_views.xml',
        'views/partner_view.xml',
        'views/account_journal_dashboard_view.xml',
        'views/mail_activity_views.xml',
        'views/res_config_settings_views.xml',
        'views/report_template.xml',
        'wizard/multicurrency_revaluation.xml',
        'wizard/report_export_wizard.xml',
        'wizard/account_report_file_download_error_wizard.xml',
        'wizard/fiscal_year.xml',
        'wizard/mail_activity_schedule_views.xml',
        'views/account_activity.xml',
        'views/account_account_views.xml',
        'views/account_tax_views.xml',
    ],
    'auto_install': True,
    'installable': True,
    'license': 'OEEL-1',
    'post_init_hook': 'set_periodicity_journal_on_companies',
    'assets': {
        'account_reports.assets_pdf_export': [
            ('include', 'web._assets_helpers'),
            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',
            ('include', 'web._assets_bootstrap_backend'),
            'web/static/fonts/fonts.scss',
            'account_reports/static/src/scss/**/*',
        ],
        'web.report_assets_common': [
            'account_reports/static/src/scss/account_pdf_export_template.scss',
        ],

        'web.assets_backend': [
            'account_reports/static/src/components/**/*',
            'account_reports/static/src/js/**/*',
            'account_reports/static/src/widgets/**/*',
        ],
        'web.assets_web_dark': [
            'account_reports/static/src/scss/*.dark.scss',
        ],
        'web.qunit_suite_tests': [
            'account_reports/static/tests/*.js',
        ],
        'web.assets_tests': [
            'account_reports/static/tests/tours/**/*',
        ],
    }
}
