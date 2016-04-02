# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Thailand - Accounting',
    'version': '1.0',
    'category': 'Localization/Account Charts',
    'description': """
Chart of Accounts for Thailand.
===============================

Thai accounting chart and localization.
    """,
    'author': 'Almacom',
    'website': 'http://almacom.co.th/',
    'depends': ['account'],
    'data': [
        'account_data.xml',
        'account_chart_template.yml',
    ],
    'installable': True,
}
