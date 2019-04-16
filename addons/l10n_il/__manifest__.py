# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Israel - Accounting',
    'version': '1.0',
    'category': 'Localization',
    'description': """
This is the latest basic Israelian localisation necessary to run Odoo in Israel:
================================================================================

This module consists:
 - Generic Israelian chart of accounts
 - Israelian taxes
 """,
    'website': 'http://www.odoo.com/accounting',
    'depends': ['account'],
    'data': [
        'data/account_chart_template_data.xml',
        'data/account.account.template.csv',
        'data/account_data.xml',
        'data/account_tax_template_data.xml',
        'data/account_chart_template_post_data.xml',
        'data/account_chart_template_configure_data.xml',
    ],
}
