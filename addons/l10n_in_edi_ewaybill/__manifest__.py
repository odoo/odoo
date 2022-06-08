# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": """Indian - E-waybill using IRN""",
    "version": "1.03.00",
    "icon": "/l10n_in/static/description/icon.png",
    "category": "Accounting/Localizations/EDI",
    "depends": [
        "l10n_in_edi",
    ],
    "description": """
Indian - E-waybill using E-invoicing
====================================
To submit E-waybill through E-invoice API to the government.
We use "Tera Software Limited" as GSP
    """,
    "data": [
        "data/account_edi_data.xml",
        "views/account_move_views.xml",
        "views/edi_pdf_report.xml",
    ],
    "installable": True,
    "auto_install": True,
    "license": "LGPL-3",
}
