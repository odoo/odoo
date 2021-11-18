# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": """E-invoicing double-check""",
    "description": """
Electronic Data Interchange double-check
========================================

EDI is the electronic interchange of business information using a standardized format.

This module for double-check before send to any API.
    """,
    "version": "1.0",
    "category": "Accounting/Accounting",
    "depends": ["account_edi"],
    "data": [
        "views/account_move_views.xml",
    ],
    "installable": True,
    "auto_install": True,
    "application": False,
    "license": "OEEL-1",
}
