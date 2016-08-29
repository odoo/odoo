# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

#    Module programed and financed by:
#    Vauxoo, C.A. (<http://vauxoo.com>).
#    Our Community team mantain this module:
#    https://launchpad.net/~openerp-venezuela

{
    'name' : 'Venezuela - Accounting',
    'author': ['Odoo S.A.', 'Vauxoo'],
    'category': 'Localization',
    'description':
"""
Chart of Account for Venezuela.
===============================

Venezuela doesn't have any chart of account by law, but the default
proposed in Odoo should comply with some Accepted best practices in Venezuela, 
this plan comply with this practices.

This module has been tested as base for more of 1000 companies, because 
it is based in a mixtures of most common software in the Venezuelan 
market what will allow for sure to accountants feel them first steps with 
Odoo more confortable.

This module doesn't pretend be the total localization for Venezuela, 
but it will help you to start really quickly with Odoo in this country.

This module give you.
---------------------

- Basic taxes for Venezuela.
- Have basic data to run tests with community localization.
- Start a company from 0 if your needs are basic from an accounting PoV.

We recomend use of account_anglo_saxon if you want valued your 
stocks as Venezuela does with out invoices.

If you install this module, and select Custom chart a basic chart will be proposed, 
but you will need set manually account defaults for taxes.
""",
    'depends': ['account',
                'base_vat',
    ],
    'data': [
             'data/l10n_ve_chart_data.xml',
             'data/account_tax_data.xml',
             'data/account_chart_template_data.yml'
    ],
}
