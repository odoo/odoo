# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Generic - Accounting',
    'version': '1.1',
    'category': 'Localization/Account Charts',
    'description': """
This is the base module to manage the generic accounting chart in Odoo.
==============================================================================

Install some generic chart of accounts.
    """,
    'author': 'Odoo',
    'depends': [
        'account',
    ],
    'data': [
        'data/configurable_account_chart.xml',
        'account_chart_template.yml',
    ],
    'test': [
        '../account/test/account_bank_statement.yml',
        #'../account/test/account_cash_statement.yml',
        '../account/test/account_invoice_state.yml',
    ],
    'demo': [
        '../account/demo/account_bank_statement.yml',
        '../account/demo/account_invoice_demo.yml',
    ],
    'installable': True,
    'website': 'https://www.odoo.com/page/accounting',
}
