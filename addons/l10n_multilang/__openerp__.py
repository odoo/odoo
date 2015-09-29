# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Multi Language Chart of Accounts',
    'version': '1.1',
    'category': 'Hidden/Dependency',
    'description': """
    * Multi language support for Chart of Accounts, Taxes, Tax Codes, Journals,
      Accounting Templates, Analytic Chart of Accounts and Analytic Journals.
    * Setup wizard changes
        - Copy translations for COA, Tax, Tax Code and Fiscal Position from
          templates to target objects.
    """,
    'depends' : ['account'],
    'data': [],
    'demo': [],
    'installable': True,
    'auto_install': False,
}
