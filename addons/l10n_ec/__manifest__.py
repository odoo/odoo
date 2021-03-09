# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2010-2012 Cristian Salamea Gnuthink Software Labs Cia. Ltda

{
    'name': 'Ecuador - Accounting',
    'icon': '/base/static/img/country_flags/ec.png',
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
        'data/account_type.xml',
        #'data/account_group_data.xml',
        'data/l10n_ec_chart_data.xml',
        #'data/l10n_ec_chart_post_data.xml',
        'data/account.tax.group.csv',
        'data/account_tax_data.xml',
        'data/account_chart_template_data.xml',
        'data/res.country.state.csv',
        'data/res.bank.csv',
        'data/account.fiscal.position.csv',

    ],
    'demo': [
        'demo/demo_company.xml',
    ],
}
