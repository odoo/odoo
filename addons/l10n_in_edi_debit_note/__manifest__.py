# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": """Debit Note For Indian - E-invoicing""",
    "version": "1.0",
    "icon": "/l10n_in/static/description/icon.png",
    "category": "Accounting",
    "depends": [
        "l10n_in_edi",
        "account_debit_note",
    ],
    "description": """
Debit Note Bridge
=================

This module enables support for debit notes in Odoo using the account_debit_note module.

This module also sets the E-invoice JSON type to DBN for debit notes.
    """,
    "installable": True,
    "auto_install": True,
    "license": "LGPL-3",
}
