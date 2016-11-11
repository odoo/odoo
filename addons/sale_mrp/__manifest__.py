# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Sales and MRP Management',
    'version': '1.0',
    'category': 'Hidden',
    'description': """
This module provides facility to the user to install mrp and sales modulesat a time.
====================================================================================

It is basically used when we want to keep track of production orders generated
from sales order. It adds sales name and sales Reference on production order.
    """,
    'website': 'https://www.odoo.com/page/manufacturing',
    'depends': ['mrp', 'sale_stock'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'demo': [],
    'test':[
        'test/cancellation_propagated.yml',
        'test/sale_mrp.yml',
        ],
    'installable': True,
    'auto_install': True,
}
