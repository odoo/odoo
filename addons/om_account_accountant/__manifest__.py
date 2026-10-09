# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Odoo 16 Accounting',
    'version': '1.0.0',
    'category': 'Accounting',
    'summary': 'Accounting Reports, Asset Management and Account Budget, Recurring Payments, '
               'Lock Dates, Fiscal Year For Odoo 16 Community Edition, Accounting Dashboard, Financial Reports, '
               'Customer Follow up Management, Bank Statement Import, Odoo Budget',
    'description': 'Odoo 16 Financial Reports, Asset Management and '
                   'Account Budget, Financial Reports, Recurring Payments, '
                   'Bank Statement Import, Customer Follow Up Management,'
                   'Account Lock Date, Accounting Dashboard',
    'live_test_url': 'https://www.youtube.com/watch?v=6gB-05E5kNg',
    'sequence': '1',
    'website': 'https://www.odoomates.tech',
    'author': 'Odoo Mates, Odoo SA',
    'maintainer': 'Odoo Mates',
    'license': 'LGPL-3',
    'support': 'odoomates@gmail.com',
    'depends': [
        'accounting_pdf_reports',
        'om_account_asset',
        'om_account_budget',
        'om_fiscal_year',
        'om_recurring_payments',
        'om_account_bank_statement_import',
        'om_account_daily_reports',
        'om_account_followup',
    ],
    'demo': [],
    'data': [
        'security/group.xml',
        'views/menu.xml',
        'views/settings.xml',
        'views/account_group.xml',
        'views/account_tag.xml',
        'views/res_partner.xml',
        'views/account_coa_template.xml',
        'views/fiscal_position_template.xml',
        'views/account_bank_statement.xml',
        'views/payment_method.xml',
        'views/reconciliation.xml',
        'views/account_journal.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': ['static/description/banner.png'],
}

