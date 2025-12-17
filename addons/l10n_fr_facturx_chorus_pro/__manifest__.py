# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'France - Peppol integration with Chorus Pro',
    'countries': ['fr'],
    'version': '1.0',
    'category': 'Accounting/Localizations/EDI',
    'description': """
Add support to fill three optional fields used when using Chorus Pro, especially when invoicing public services.
""",
    'depends': [
        'account',
        'account_edi_ubl_cii',
        'l10n_fr_account',
    ],
    'data': [
        'views/account_move_views.xml',
        'views/report_invoice.xml',
    ],
    'license': 'LGPL-3',
}
