# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Indian - Debit Notes',
    'version': '1.0',
    'category': 'Accounting/Localizations',
    'description': """
Indian - Debit Notes
=========================
Adds a new sequence when creating debit notes and adds menu
for viewing customer and vendor debit notes.
    """,
    'depends': ['l10n_in', 'account_debit_note'],
    'data': [
        'views/account_debit_note_menus.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
