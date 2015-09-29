# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2011 Cubic ERP - Teradata SAC. (http://cubicerp.com).

{
    "name": "Panama - Accounting",
    "version": "1.0",
    "description": """
Panamenian accounting chart and tax localization.

Plan contable panameño e impuestos de acuerdo a disposiciones vigentes

Con la Colaboración de
- AHMNET CORP http://www.ahmnet.com

    """,
    "author": "Cubic ERP",
    "website": "http://cubicERP.com",
    "category": "Localization/Account Charts",
    "depends": ["account"],
    "data": [
        "l10n_pa_chart.xml",
        "account_tax.xml",
        "account_chart_template.yml",
    ],
    "demo_xml": [],
    "installable": True,
    "certificate": "",
}
