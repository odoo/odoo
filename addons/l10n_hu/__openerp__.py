# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2014 InnOpen Group Kft (<http://www.innopen.eu>).

{
    'name': 'Hungarian - Accounting',
    'version': '2.0',
    'category': 'Localization',
    'description': """

Base module for Hungarian localization
==========================================

This module consists :

 - Generic Hungarian chart of accounts
 - Hungarian taxes
 - Hungarian Bank information
 """,
    'author': 'InnOpen Group Kft',
    'website': 'http://www.innopen.eu',
    'depends': ['account'],
    'data': [
        'data/account_chart_template.xml',
        'data/account.account.template.csv',
        'data/account.account.tag.csv',
        'data/account.tax.template.csv',
        'data/account.fiscal.position.template.csv',
        'data/account.fiscal.position.tax.template.csv',
        'data/res.bank.csv',
        'data/account_chart_template_after.xml',
        'data/account_chart_template.yml',
    ],
    'installable': True,
    'auto_install': False,
}
