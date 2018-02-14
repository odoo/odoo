# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Dummy Invoice",
    "author": "Vauxoo",
    "category": "Accounting",
    "description": """
        A dummy module to test QR printing.
    """,
    "depends": [
        "account",
    ],
    "data": [
        "views/report_invoice_dummy.xml",
    ],
   "installable": True,
   "application": True,
   "auto_install": False,
}
