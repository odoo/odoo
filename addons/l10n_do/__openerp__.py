# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# First author: Jose Ernesto Mendez <tecnologia@obsdr.com> (Open Business Solutions SRL.)
# Copyright (c) 2012 -TODAY Open Business Solutions, SRL. (http://obsdr.com). All rights reserved.
# This is a fork to upgrade to odoo 8.0
# by Marcos Organizador de Negocios - Eneldo Serrata - www.marcos.org.do

{
    'name': 'Dominican Republic - Accounting',
    'version': '1.0',
    'category': 'Localization/Account Charts',
    'description': """
This is the base module to manage the accounting chart for Dominican Republic.
==============================================================================

* Chart of Accounts.
* The Tax Code Chart for Domincan Republic
* The main taxes used in Domincan Republic
* Fiscal position for local """,
    'author': 'Eneldo Serrata - Marcos Organizador de Negocios, SRL.',
    'website': 'http://marcos.do',
    'depends': ['account', 'base_iban'],
    'data': [
        # basic accounting data
        'data/account_chart_template.xml',
        'data/account.account.template.csv',
        'data/set_account_on_chart_template.xml',
        'data/account_account_tag.xml',
        'data/account.tax.template.csv',
        'data/l10n_do_base_data.xml',
        # Adds fiscal position
        'data/account.fiscal.position.template.csv',
        'data/account.fiscal.position.tax.template.csv',
        # configuration wizard, views, reports...
        'data/account_chart_template.yml',
    ],
    'test': [],
    'demo': [],
    'installable': True,
    'auto_install': False,
}
