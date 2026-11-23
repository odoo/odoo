# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Purchase Requisition Sale',
    'description': "Bridge module for Purchase requisition and Sales. Used to properly create purchase requisitions for subcontracted services",
    'version': '1.0',
    'category': 'Inventory/Purchase',
    'sequence': 70,
    'depends': ['purchase_requisition', 'sale_purchase'],
    'auto_install': True,
    'license': 'LGPL-3',
}
