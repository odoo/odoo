# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Purchase Requisition Stock',
    'version': '1.2',
    'category': 'Inventory/Purchase',
    'sequence': 70,
    'summary': '',
    'description': "",
    'depends': ['purchase_requisition', 'purchase_stock'],
    'demo': [
        'data/purchase_requisition_stock_demo.xml'
        ],
    'data': [
        'security/ir.model.access.csv',
        'data/purchase_requisition_stock_data.xml',
        'views/purchase_requisition_views.xml',
    ],
    'installable': True,
    'auto_install': True,
}
