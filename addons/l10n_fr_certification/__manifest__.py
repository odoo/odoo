# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'France - Accounting - Certified CGI 286 I-3 bis',
    'version': '1.0',
    'category': 'Localization',
    'description': """
""",
    'depends': ['l10n_fr'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'data': [
        'views/no_cancel.xml',
        'data/account_move.xml',
    ],
    'post_init_hook': '_setup_inalterability',
}
