# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2015 Willow IT Pty Ltd (<http://www.willowit.com.au>).

{
    'name': 'Australian - Accounting',
    'version': '1.1',
    'category': 'Localization',
    'description': """
Australian Accounting Module
============================

Australian accounting basic charts and localizations.

Also:
    - activates a number of regional currencies.
    - sets up Australian taxes.
    """,
    'author': 'Richard deMeester - Willow IT',
    'website': 'http://www.willowit.com',
    'depends': ['account'],
    'data': [
             'data/l10n_au_chart_data.xml',
             'data/account.account.template.csv',
             'data/account_chart_template_data.xml',
             'data/account.account.tag.csv',
             'data/account.tax.group.csv',
             'data/account.tax.template.csv',
             'data/account_fiscal_position_tax_template_data.xml',
             'data/account_chart_template_data.yml',
             'data/res_currency_data.xml',
             ],
}
