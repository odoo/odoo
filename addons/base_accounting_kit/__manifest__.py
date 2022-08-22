# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2021-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################

{
    'name': 'Odoo 15 Full Accounting Kit',
    'version': '15.0.2.2.2',
    'category': 'Accounting',
    'live_test_url': 'https://www.youtube.com/watch?v=peAp2Tx_XIs',
    'summary': """ Asset and Budget Management,
                 Accounting Reports, PDC, Lock dates,
                 Credit Limit, Follow Ups,
                 Day-Bank-Cash book reports.""",
    'description': """
                    AccountingKit, Fullaccounting, Odoo accounting, Odooaccounting, all in one accounting,
                    allinoneaccounting, accounting,
                    Odoo 15 Accounting,Accounting Reports, Odoo 15 Accounting
                    PDF Reports, Asset Management, Budget Management,
                    Customer Credit Limit, Recurring Payment,
                    PDC Management, Customer Follow-up,
                    Lock Dates into Odoo 15 Community Edition,
                    Odoo Accounting,Odoo 15 Accounting Reports,Odoo 15,,
                    Full Accounting, Complete Accounting,
                    Odoo Community Accounting, Accounting for odoo 15,
                    Full Accounting Package,
                    Financial Reports, Financial Report for Odoo 15,
                    Reconciliation Widget,
                    Reconciliation Widget For Odoo15,
                    Payments Matching
                    """,
    'author': 'Cybrosys Techno Solutions, Odoo SA',
    'website': "https://www.cybrosys.com",
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'depends': ['base', 'account', 'sale', 'account_check_printing', 'base_account_budget'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/account_financial_report_data.xml',
        'data/cash_flow_data.xml',
        'data/account_pdc_data.xml',
        'data/followup_levels.xml',
        'data/account_asset_data.xml',
        'data/recurring_entry_cron.xml',
        'data/multiple_invoice_data.xml',
        'views/assets.xml',
        'views/dashboard_views.xml',
        'views/reports_config_view.xml',
        'views/accounting_menu.xml',
        'views/account_group.xml',
        'views/credit_limit_view.xml',
        'views/account_configuration.xml',
        'views/account_payment_view.xml',
        'views/res_config_view.xml',
        'views/recurring_payments_view.xml',
        'views/account_followup.xml',
        'views/followup_report.xml',
        'wizard/asset_depreciation_confirmation_wizard_views.xml',
        'wizard/asset_modify_views.xml',
        'views/account_asset_views.xml',
        'views/account_move_views.xml',
        'views/account_asset_templates.xml',
        'views/product_template_views.xml',
        'views/payment_matching.xml',
        'views/multiple_invoice_layout_view.xml',
        'views/multiple_invoice_form.xml',
        'wizard/financial_report.xml',
        'wizard/general_ledger.xml',
        'wizard/partner_ledger.xml',
        'wizard/tax_report.xml',
        'wizard/account_lock_date.xml',
        'wizard/trial_balance.xml',
        'wizard/aged_partner.xml',
        'wizard/journal_audit.xml',
        'wizard/cash_flow_report.xml',
        'wizard/account_bank_book_wizard_view.xml',
        'wizard/account_cash_book_wizard_view.xml',
        'wizard/account_day_book_wizard_view.xml',
        'report/report_financial.xml',
        'report/general_ledger_report.xml',
        'report/report_journal_audit.xml',
        'report/report_aged_partner.xml',
        'report/report_trial_balance.xml',
        'report/report_tax.xml',
        'report/report_partner_ledger.xml',
        'report/cash_flow_report.xml',
        'report/account_bank_book_view.xml',
        'report/account_cash_book_view.xml',
        'report/account_day_book_view.xml',
        'report/account_asset_report_views.xml',
        'report/report.xml',
        'report/multiple_invoice_layouts.xml',
        'report/multiple_invoice_report.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'base_accounting_kit/static/src/scss/style.scss',
            'base_accounting_kit/static/src/scss/account_asset.scss',
            'base_accounting_kit/static/lib/bootstrap-toggle-master/css/bootstrap-toggle.min.css',
            'base_accounting_kit/static/src/js/account_dashboard.js',
            'base_accounting_kit/static/src/js/account_asset.js',
            'base_accounting_kit/static/src/js/payment_model.js',
            'base_accounting_kit/static/src/js/payment_render.js',
            'base_accounting_kit/static/src/js/payment_matching.js',
            'base_accounting_kit/static/lib/Chart.bundle.js',
            'base_accounting_kit/static/lib/Chart.bundle.min.js',
            'base_accounting_kit/static/lib/Chart.min.js',
            'base_accounting_kit/static/lib/Chart.js',
            'base_accounting_kit/static/lib/bootstrap-toggle-master/js/bootstrap-toggle.min.js',

        ],
        'web.assets_qweb': [
            'base_accounting_kit/static/src/xml/template.xml',
            'base_accounting_kit/static/src/xml/payment_matching.xml',
        ],
    },
    'license': 'LGPL-3',
    'images': ['static/description/banner.gif'],
    'installable': True,
    'auto_install': False,
    'application': True,
}
