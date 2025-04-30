# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Purchase Requisition Sale',
    'description': "Bridge module for Purchase requisition and Sales. Used to properly create purchase requisitions for subcontracted services",
    'version': '1.0',
    'category': 'Supply Chain/Purchase',
    'sequence': 70,
    'depends': ['purchase_requisition', 'sale_purchase'],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
