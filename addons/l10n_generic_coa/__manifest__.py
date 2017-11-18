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
        'data/account_chart_template_data.xml',
    ],
    'demo': [
        'data/account_bank_statement_demo.xml',
        'data/account_invoice_demo.xml',
    ],
    'website': 'https://www.odoo.com/page/accounting',
}
