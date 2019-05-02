# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Copyright (C) 2019 Bohdan Lisnenko <bohdan.lisnenko@erp.co.ua>, ERP Ukraine

{
    'name': 'Ukraine - Accounting',
    'author': 'ERP Ukraine',
    'website': 'https://erp.co.ua',
    'version': '1.3',
    'description': """
Ukraine - Chart of accounts.
============================
    """,
    'category': 'Localization',
    'depends': ['account'],
    'data': [
        'data/account_chart_template.xml',
        'data/account.account.template.csv',
        'data/account_account_tag_data.xml',
        'data/account_tax_tag_data.xml',
        'data/account_tax_group_data.xml',
        'data/account_tax_template.xml',
        'data/account_chart_template_config.xml',
    ],
}
