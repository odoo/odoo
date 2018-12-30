# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Account Tax Cash Basis',
    'version' : '1.1',
    'summary': 'Allow to have cash basis on tax',
    'sequence': 4,
    'description': """
    Add an option on tax to allow them to be cash based, meaning that during reconciliation, if there is a tax with
    cash basis involved, a new journal entry will be create containing those taxes value.
    """,
    'category': 'Accounting',
    'website': 'https://www.odoo.com/page/accounting',
    'depends' : ['account'],
    'data': [
        'views/tax_cash_basis_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}
