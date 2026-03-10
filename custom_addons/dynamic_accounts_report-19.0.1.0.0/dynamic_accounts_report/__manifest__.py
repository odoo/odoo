# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Swetha Anand (<https://www.cybrosys.com>)
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
################################################################################
{
    'name': 'Odoo19 Dynamic Accounting Reports',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': "Odoo 19 Accounting Financial Reports,Dynamic Accounting Reports, Dynamic Financial Reports,Dynamic Report Odoo18, Odoo18,Financial Reports, Odoo18 Accounting,Accounting, Odoo Apps",
    'description': "This module creates dynamic Accounting General Ledger, Trial"
                   "Balance, Balance Sheet, Profit and Loss, Cash Book, Partner"
                   "Ledger, Aged Payable, Aged Receivable, Bank book and Tax"
                   "Reports in Odoo 19 community edition, Reporting, Odoo18 Accounting, odoo18 reporting, odoo18, odoo18 accounts reports",
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': "https://www.cybrosys.com",
    'depends': ['base_accounting_kit'],
    'data': [
        'security/ir.model.access.csv',
        'views/accounting_report_views.xml',
        'report/trial_balance.xml',
        'report/general_ledger_templates.xml',
        'report/financial_report_template.xml',
        'report/partner_ledger_templates.xml',
        'report/financial_reports_views.xml',
        'report/balance_sheet_report_templates.xml',
        'report/bank_book_templates.xml',
        'report/aged_payable_templates.xml',
        'report/aged_receivable_templates.xml',
        'report/tax_report_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'dynamic_accounts_report/static/src/xml/general_ledger_view.xml',
            'dynamic_accounts_report/static/src/xml/trial_balance_view.xml',
            'dynamic_accounts_report/static/src/xml/cash_flow_templates.xml',
            'dynamic_accounts_report/static/src/xml/bank_flow_templates.xml',
            'dynamic_accounts_report/static/src/xml/profit_and_loss_templates.xml',
            'dynamic_accounts_report/static/src/xml/balance_sheet_template.xml',
            'dynamic_accounts_report/static/src/xml/partner_ledger_view.xml',
            'dynamic_accounts_report/static/src/xml/aged_payable_report_views.xml',
            'dynamic_accounts_report/static/src/xml/aged_receivable_report_views.xml',
            'dynamic_accounts_report/static/src/xml/tax_report_views.xml',
            'dynamic_accounts_report/static/src/css/accounts_report.css',
            'dynamic_accounts_report/static/src/js/general_ledger.js',
            'dynamic_accounts_report/static/src/js/trial_balance.js',
            'dynamic_accounts_report/static/src/js/cash_flow.js',
            'dynamic_accounts_report/static/src/js/bank_flow.js',
            'dynamic_accounts_report/static/src/js/profit_and_loss.js',
            'dynamic_accounts_report/static/src/js/balance_sheet.js',
            'dynamic_accounts_report/static/src/js/partner_ledger.js',
            'dynamic_accounts_report/static/src/js/aged_payable_report.js',
            'dynamic_accounts_report/static/src/js/aged_receivable_report.js',
            'dynamic_accounts_report/static/src/js/tax_report.js',
        ],
    },
    'images': ['static/description/banner.gif'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
