# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2010-2012 Cristian Salamea Gnuthink Software Labs Cia. Ltda

{
    'name': 'Ecuador - Accounting',
    'version': '1.1',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This is the base module to manage the accounting chart for Ecuador in Odoo.
==============================================================================

Accounting chart and localization for Ecuador.
    """,
    'author': 'Gnuthink Co.Ltd.',
    'depends': [
        'account',
        'base_iban',
        'l10n_latam_base',
        'l10n_latam_invoice_document',
    ],
    'data': [
        'data/l10n_ec_chart_data.xml',
        'data/account.account.template.csv',
        'data/l10n_ec_chart_post_data.xml',
        'data/account_data.xml',
        'data/account_tax_data.xml',
        'data/account_chart_template_data.xml',
        'data/res.country.state.csv',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
