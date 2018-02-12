# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Purchase Stock',
    'version': '1.2',
    'category': 'Purchases',
    'sequence': 60,
    'summary': 'Purchase Orders, Receipts, Vendor Bills for Stock',
    'description': "",
    'website': 'https://www.odoo.com/page/purchase',
    'depends': ['stock_account', 'purchase'],
    'data': [
        'views/stock_views.xml',
    ],
    'installable': True,
    'auto_install': True,
}
