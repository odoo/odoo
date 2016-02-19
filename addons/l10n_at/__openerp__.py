# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) conexus.at

{
    'name': 'Austria - Accounting',
    'version': '2.0',
    'author': 'conexus.at',
    'website': 'http://www.conexus.at',
    'category': 'Localization/Account Charts',
    'depends': ['base_vat'],
    'description': """
This module provides the standard Accounting Chart for Austria which is based on the Template from BMF.gv.at.
============================================================================================================= 
Please keep in mind that you should review and adapt it with your Accountant, before using it in a live Environment.
""",
    'demo': [],
    'data': ['account_chart.xml', 'account_tax.xml', 'account_chart_template.yml'],
    'auto_install': False,
    'installable': True
}
