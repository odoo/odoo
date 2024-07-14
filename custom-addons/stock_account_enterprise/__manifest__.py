# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Stock account enterprise",
    'version': "1.0",
    'category': 'Inventory/Inventory',
    'summary': "Advanced features for stock_account",
    'description': """
Contains the enterprise views for Stock account
    """,
    'depends': ['stock_account', 'stock_enterprise'],
    'installable': True,
    'auto_install': ['stock_account'],
    'license': 'OEEL-1',
}
