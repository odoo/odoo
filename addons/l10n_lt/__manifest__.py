# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Lithuania - Chart of Accounts',
    'version': '1.0',
    'author': 'UAB Versada',
    'category': 'Localization',
    'website': 'https://versada.eu/',
    'depends': [
        'account',
    ],
    'description': """
This is the base module to manage the accounting chart for Lithuania in Odoo.
==============================================================================

Creates chart of accounts based on avnt.lt provided Example Chart of Accounts
version validated on 2016-01-28.

After installing this module make sure to check "Liquidity Transfer", "Bank",
"Cash" accounts and convert them to the ones corresponding with VAS if needed.
    """,
    'data': [
        'data/account_chart_template_1.xml',
        'data/account_account_template_2.xml',
        'data/account_chart_template_2.xml',
        'data/account_tax_template.xml',
        'data/account_fiscal_position_template.xml',
        'data/account_initiate_chart.xml',
    ],
    'installable': True,
}
