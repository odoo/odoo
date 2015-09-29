# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2011 Cubic ERP - Teradata SAC. (https://cubicerp.com).

{
    "name": "Bolivia - Accounting",
    "version": "1.0",
    "description": """
Bolivian accounting chart and tax localization.

Plan contable boliviano e impuestos de acuerdo a disposiciones vigentes

    """,
    "author": "Cubic ERP",
    "website": "https://cubicERP.com",
    "category": "Localization/Account Charts",
    "depends": ["account"],
    "data": [
        "l10n_bo_chart.xml",
        "account_tax.xml",
        "account_chart_template.yml",
    ],
    "installable": True,
}
