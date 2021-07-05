# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Indian - Accounting Multi Parent tax fix",
    "version": "1.0",
    "description": """
Indian Accounting: Multi Parent tax fix.
====================================

When There is child tax is use more then one time in group of tax then GSTR1 report line is duplicated.
Using this module you can fix it.

Note: This give purformence issue if there is too much data.
  """,
    "category": "Accounting/Localizations",
    "depends": [
        "l10n_in",
    ],
    "data": [],
}
