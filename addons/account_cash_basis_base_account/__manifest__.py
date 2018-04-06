# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Tax Cash Basis Edit Base Account',
    'version' : '1.0',
    'summary': 'Add a custom account to handle base amount lines',
    'sequence': 5,
    'description': """
Move the cash basis lines to another account.
    """,
    'category': 'Accounting',
    'depends': ['account'],
    'data': [
        'views/account_tax_views.xml',
    ],
    'installable': True,
    'auto_install': True,
}
