# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'France - Factur-X integration with Chorus Pro',
    'version': '1.0',
    'category': 'Accounting/Localizations/EDI',
    'description': """
Add supports to fill three optional fields used when using Chorus Pro, especially when invoicing public services.
""",
    'depends': [
        'account',
        'account_edi_facturx',
        'l10n_fr'
    ],
    'data': [
        'views/account_move_views.xml',
    ],
    'license': 'LGPL-3',
}
