# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Thailand - Accounting',
    'version': '2.0',
    'category': 'Localization',
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
    'post_init_hook': '_preserve_tag_on_taxes',
}
