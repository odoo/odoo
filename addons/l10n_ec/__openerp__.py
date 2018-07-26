# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2010-2012 Cristian Salamea Gnuthink Software Labs Cia. Ltda

{
    'name': 'Ecuador - Accounting',
    'version': '1.1',
    'category': 'Localization',
    'description': """
This is the base module to manage the accounting chart for Ecuador in OpenERP.
==============================================================================

Accounting chart and localization for Ecuador.
    """,
    'author': 'Gnuthink Co.Ltd.',
    'depends': [
        'account',
        'base_vat',
        'base_iban',
    ],
    'data': [
        'account_chart.xml',
        'account_tax.xml',
        'account_chart_template.yml',
    ],
    'demo': [],
    'installable': True,
}
