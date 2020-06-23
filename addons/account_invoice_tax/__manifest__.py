# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Account Invoice Tax',
    'version': "1.0",
    'description': """
Functional
----------

Add new button in the Vendor Bills that let us to add new taxes to all the lines
of a vendor bill.
""",
    'author': 'ADHOC SA',
    'category': 'Localization',
    'depends': [
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_view.xml',
        'wizards/res_partner_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
