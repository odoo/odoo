#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2012 Michael Telahun Makonnen <mmakonnen@gmail.com>.

{
    'name': 'Ethiopia - Accounting',
    'version': '2.0',
    'category': 'Localization',
    'description': """
Base Module for Ethiopian Localization
======================================

This is the latest Ethiopian OpenERP localization and consists of:
    - Chart of Accounts
    - VAT tax structure
    - Withholding tax structure
    - Regional State listings
    """,
    'author':'Michael Telahun Makonnen <mmakonnen@gmail.com>',
    'website':'http://miketelahun.wordpress.com',
    'depends': [
        'base_vat',
    ],
    'data': [
        'data/account_chart_template.xml',
        'data/account.account.template.csv',
        'data/set_account_on_chart_template.xml',
        'data/account_account_tag.xml',
        'data/account.tax.template.csv',
        'data/account_chart_template.yml',
        'data/res.country.state.csv',
    ],
    'installable': True,
    'active': False,
}
