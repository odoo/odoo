# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Copyright (C) 2009  Renato Lima - Akretion

{
    'name': 'Brazilian - Accounting',
    'category': 'Localization',
    'description': """
Base module for the Brazilian localization
==========================================

This module consists in:

 - Generic Brazilian chart of accounts
 - Brazilian taxes

It's important to note however that this module lack many implementations to
use Odoo properly in Brazil. Those implementations (such as the electronic
fiscal Invoicing which is already operational) are brought by more than 30
additional modules of the Brazilian localization project
https://github.com/OCA/l10n-brazil and their dependencies in the
extra addons branch. Those modules aim at not breaking with the remarkable
Odoo modularity, this is why they are numerous but small. One of the
reasons for maintaining those modules apart is that Brazilian Localization
leaders need commit rights agility to complete the localization as companies
fund the remaining legal requirements (such as soon fiscal ledgers,
accounting SPED and fiscal SPED). Those modules are also strictly licensed
under AGPL V3 and today don't come with any additional paid permission for
online use of 'private modules'.
""",
    'author': 'Akretion, Odoo Brasil',
    'website': 'http://github.com/OCA/l10n-brazil',
    'depends': ['account'],
    'data': [
        'data/l10n_br_chart_data.xml',
        'data/account_group_data.xml',
        'data/account.account.template.csv',
        'data/account_data.xml',
        'data/account_tax_report_data.xml',
        'data/account_tax_template_data.xml',
    ],
}
