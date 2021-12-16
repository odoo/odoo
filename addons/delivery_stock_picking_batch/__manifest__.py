# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Delivery Stock Picking Batch',
    'version': '1.0',
    'category': 'Hidden',
    'summary': 'Batch Transfer, Carrier',
    'description': """
This module makes the link between the batch pickings and carrier applications.

Allows to prepare batches depending on their carrier
""",
    'depends': ['delivery', 'stock_picking_batch'],
    'data': [
        'views/stock_picking_type_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
