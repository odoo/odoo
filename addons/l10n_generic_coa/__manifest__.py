# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Generic - Accounting',
    'version': '1.1',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This is the base module to manage the generic accounting chart in Odoo.
==============================================================================

Install some generic chart of accounts.
    """,
    'depends': [
        'account',
    ],
    'data': [
        'data/l10n_generic_coa.xml',
        'data/account.account.template.csv',
        'data/l10n_generic_coa_post.xml',
    ],
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
