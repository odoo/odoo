# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2011 Cubic ERP - Teradata SAC. (http://cubicerp.com)

{
    'name': 'Argentina - Accounting',
    'version': '2.0',
    'description': """
Argentinian accounting chart and tax localization.
==================================================

Plan contable argentino e impuestos de acuerdo a disposiciones vigentes

    """,
    'author': ['Cubic ERP'],
    'website': 'http://cubicERP.com',
    'category': 'Localization',
    'depends': ['base', 'account'],
    'data':[
        'data/l10n_ar_chart_data.xml',
        'data/account_data.xml',
        'data/account_tax_data.xml',
        'data/account_chart_template_data.yml',
    ],
}
