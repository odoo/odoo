# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Hungarian Invoicing Localisation",
    "version": "16.0.1.0.0",
    "icon": "/l10n_hu/static/description/icon.png",
    "category": "Accounting/Localizations/EDI",
    "author": "OdooTech Zrt. & BDSC Business Consulting Kft.",
    "description": """
Hungarian Invoicing extension.
==============================

With this module you can issue a hungarian invoice.
    """,
    "website": "https://www.odootech.hu",
    "depends": [
        "l10n_hu",
        "account",
        "account_edi",
        "base_vat",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/nav_communication.xml",
        "data/nav_invoice.xml",
        "data/nav_aea_xml.xml",
        "data/load_xsd_data.xml",
        "data/uom_uom.xml",
        "data/account_edi_data.xml",
        "views/report_templates.xml",
        "views/report_invoice.xml",
        "views/l10n_hu_nav_communication.xml",
        "views/l10n_hu_nav_transaction.xml",
        "views/account_move.xml",
        "views/product.xml",
        "views/account_tax.xml",
        "views/uom.xml",
        "views/res_partner.xml",
        "views/res_company.xml",
        "views/res_config_settings_views.xml",
        "wizard/nav_aea_xml_export.xml",
    ],
    "demo": [
        "demo/demo_partner.xml",
        "demo/demo_company.xml",
    ],
    "post_init_hook": "post_init",
    "installable": True,
    "auto_install": ["l10n_hu", "account"],
    "license": "LGPL-3",
}
