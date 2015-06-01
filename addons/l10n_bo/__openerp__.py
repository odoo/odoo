# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2011 Cubic ERP - Teradata SAC. (http://cubicerp.com).

{
    "name": "Bolivia Localization Chart Account",
    "version": "1.0",
    "description": """
Bolivian accounting chart and tax localization.

Plan contable boliviano e impuestos de acuerdo a disposiciones vigentes

    """,
    "author": "Cubic ERP",
    "website": "http://cubicERP.com",
    "category": "Localization/Account Charts",
    "depends": ["account"],
    "data": [
        "l10n_bo_chart.xml",
        "account_tax.xml",
        "l10n_bo_wizard.xml",
    ],
    "demo_xml": [],
    "data": [],
    "installable": False,
    "certificate": "",

}
