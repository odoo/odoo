# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'France - BIS3 integration for Chorus Pro',
    'countries': ['fr'],
    'version': '1.0',
    'category': 'Accounting/Localizations/EDI',
    'description': """
Add support to fill three fields used when using Chorus Pro, especially when invoicing public services.
""",
    'depends': [
        'account',
        'account_edi_ubl_cii',
        'l10n_fr_account',
    ],
    'data': [
        'views/account_move_views.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
