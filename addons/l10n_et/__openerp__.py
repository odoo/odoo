#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2012 Michael Telahun Makonnen <mmakonnen@gmail.com>.

{
    'name': 'Ethiopia - Accounting',
    'version': '1.0',
    'category': 'Localization/Account Charts',
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
    'init_xml': [
        'data/account.account.type.csv',
        'data/account.account.template.csv',
        'data/account.chart.template.csv',
        'data/account.tax.template.csv',
        'data/res.country.state.csv',
    ],
    'data': [
        'l10n_et_wizard.xml',
    ],
    'test': [
    ],
    'demo': [
    ],
    'installable': False,
    'active': False,
}
