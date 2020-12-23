# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2009-2016 Salvatore Josué Trimarchi Pinto <trimarchi@bacgroup.net>

# This module provides a minimal Honduran chart of accounts that can be use
# to build upon a more complex one.  It also includes a chart of taxes and
# the Lempira currency.

{
    'name': 'Honduras - Accounting',
    'version': '0.2',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This is the base module to manage the accounting chart for Honduras.
====================================================================

Agrega una nomenclatura contable para Honduras. También incluye impuestos y la
moneda Lempira. -- Adds accounting chart for Honduras. It also includes taxes
and the Lempira currency.""",
    'author': 'Salvatore Josue Trimarchi Pinto',
    'website': 'http://bacgroup.net',
    'depends': ['base', 'account'],
    'data': [
        'data/l10n_hn_chart_data.xml',
        'data/account.account.template.csv',
        'data/l10n_hn_chart_post_data.xml',
        'data/account_data.xml',
        'data/account_chart_template_data.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
}
