# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'MTO Sale <-> Purchase',
    'version': '1.0',
    'category': 'Hidden',
    'summary': 'SO/PO relation in case of MTO',
    'description': """
Add relation information between Sale Orders and Purchase Orders if Make to Order (MTO) is activated on one sold product.
""",
    'depends': ['sale_stock', 'purchase_stock', 'sale_purchase'],
    'data': [],
    'demo': [],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
