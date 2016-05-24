# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2010-2012 Cristian Salamea Gnuthink Software Labs Cia. Ltda

{
    'name': 'Ecuador - Accounting',
    'version': '1.1',
    'category': 'Localization',
    'description': """
This is the base module to manage the accounting chart for Ecuador in Odoo.
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
        'data/l10n_ec_chart_data.xml',
        'data/account_tax_data.xml',
        'data/account_chart_template_data.yml',
    ],
}
