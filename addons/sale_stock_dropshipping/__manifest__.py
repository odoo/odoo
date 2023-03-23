# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Sale Drop Shipping',
    'version': '1.0',
    'category': 'Hidden',
    'summary': 'Sale Drop Shipping',
    'description': """
        This bridge module allows to manage sale orders with the dropshipping module.
    """,
    'depends': ['sale', 'stock_dropshipping'],
    'data': [
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
