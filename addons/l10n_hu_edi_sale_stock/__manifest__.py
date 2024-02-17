# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Hungarian Invoicing Localisation - Sale-Stock",
    "version": "16.0.1.0.0",
    "icon": "/l10n_hu/static/description/icon.png",
    "category": "Accounting/Localizations/EDI",
    "author": "OdooTech Zrt., BDSC Business Consulting Kft., Odoo S.A.",
    "description": """
Hungarian Invoicing and Sale integration
========================================

This is a glue module between Hungarian EDI and Sale
    """,
    "website": "https://www.odootech.hu",
    "depends": [
        "l10n_hu_edi",
        "sale_stock",
    ],
    "data": [],
    "demo": [],
    "installable": True,
    "auto_install": True,
    "license": "LGPL-3",
}
