# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2011 Cubic ERP - Teradata SAC. (http://cubicerp.com).

{
    'name': 'Chile - Accounting',
    'version': '2.0',
    'description': """
Chilean accounting chart and tax localization.
==============================================
Plan contable chileno e impuestos de acuerdo a disposiciones vigentes

    """,
    'author': 'Cubic ERP',
    'category': 'Localization',
    'depends': ['account'],
    'data': [
        'data/l10n_cl_chart_data.xml',
        'data/account_data.xml',
        'data/account_tax_data.xml',
        'data/account_chart_template_data.xml',
    ],
}
