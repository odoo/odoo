# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Purchase Requisition Stock Dropshipping',
    'version': '1.0',
    'category': 'Hidden',
    'summary': 'Purchase Requisition, Stock, Dropshipping',
    'description': """
This module makes the link between the purchase requisition and dropshipping applications.

Set shipping address on purchase orders created from purchase agreements
and link with originating sale order.
""",
    'depends': ['purchase_requisition_stock', 'stock_dropshipping'],
    'data': [
        'views/purchase_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
