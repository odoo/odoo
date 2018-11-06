# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Bridge between Inventory, Sales and Purchase',
    'version': '1.0',
    'category': 'Hidden',
    'description': """
The modules transfert the Sales Order Item to the purchase created from a Sales Order so it can be linked to the origin Sales Order.
    """,
    'depends': ['sale_purchase', 'sale_stock'],
    'auto_install': True,
}
