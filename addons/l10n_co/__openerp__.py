# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Colombian - Accounting NIIF',
    'author': 'DevCO Colombia SAS',
    'maintainer': 'DevCO Colombia',
    'website': 'http://devco.co',
    'contributors': ['Juan Pablo Arias <jpa@devco.co>','David Arnold <dar@devco.co>'],
    'version': '1.0',
    'category': 'Localization/Account Charts',
    'description': 'Colombian Accounting Preconfiguration - IFRS ready',
    'depends': [
        'account',
        'base_vat',
    ],
    'data': [
        'data/data_account_type.xml',
        'data/account_account_template.xml',
        'data/account_chart_template.xml',
        'data/account_chart_template.yml',
    ],
    'demo': [],
    'installable': True,
}
