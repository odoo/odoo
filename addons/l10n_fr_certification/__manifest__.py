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
    # According to http://proxy-pubminefi.diffusion.finances.gouv.fr/pub/document/18/22503.pdf dated June 15th 2017, the certification will only be required for POS software, not for accounting software. So only shops with POS will need the certification, not all French companies. So we switch auto_install to False.
    'auto_install': False,
    'application': True,
    'data': [
        'views/no_cancel.xml',
        'data/account_move.xml',
    ],
    'post_init_hook': '_setup_inalterability',
}
