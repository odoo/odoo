# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Generic - Accounting',
    'version': '1.1',
    'category': 'Localization',
    'description': """
This is the base module to manage the generic accounting chart in Odoo.
==============================================================================

Install some generic chart of accounts.
    """,
    'depends': [
        'account',
    ],
    'data': [
        'data/account_data.xml',
        'data/l10n_generic_coa_chart_data.xml',
        'data/account_chart_template_data.yml',
    ],
    'test': [
        '../account/test/account_bank_statement.yml',
        '../account/test/account_invoice_state.yml',
    ],
    'demo': [
        '../account/demo/account_bank_statement.yml',
        '../account/demo/account_invoice_demo.yml',
    ],
    'website': 'https://www.odoo.com/page/accounting',
}
