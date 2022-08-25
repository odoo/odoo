# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2011 Cubic ERP - Teradata SAC. (https://cubicerp.com).

{
    "name": "Bolivia - Accounting",
    "version": "2.0",
    "description": """
Bolivian accounting chart and tax localization.

Plan contable boliviano e impuestos de acuerdo a disposiciones vigentes

    """,
    "author": "Cubic ERP",
    'category': 'Accounting/Localizations/Account Charts',
    "depends": ["account"],
    "data": [
        "data/l10n_bo_chart_data.xml",
        "data/account.account.template.csv",
        "data/l10n_bo_chart_post_data.xml",
        'data/account_tax_group_data.xml',
        'data/account_tax_report_data.xml',
        "data/account_tax_data.xml",
        "data/account_chart_template_data.xml",
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
