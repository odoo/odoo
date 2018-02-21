# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) Quartile Limited

{
    'name': 'Japan - Accounting',
    'version': '2.0',
    'category': 'Localization',
    'description': """

Overview:
---------

* Chart of Accounts and Taxes template for companies in Japan.
* This probably does not cover all the necessary accounts for a company. \
You are expected to add/delete/modify accounts based on this template.

Note:
-----

* Fiscal positions '内税' and '外税' have been added to handle special \
requirements which might arise from POS implementation. [1]  You may not \
need to use these at all under normal circumstances.

[1] See https://github.com/odoo/odoo/pull/6470 for detail.

    """,
    'author': 'Quartile Limited',
    'website': 'https://www.odoo-asia.com/',
    'depends': ['account'],
    'data': [
        'data/l10n_jp_chart_data.xml',
        'data/account.account.template.csv',
        'data/account.tax.group.csv',
        'data/account.tax.template.csv',
        'data/account_chart_template_data.xml',
        'data/account.fiscal.position.template.csv',
        'data/account.fiscal.position.tax.template.csv',
        'data/account_chart_template_data.yml',
    ],
}
