# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Purchase and Subcontracting Management',
    'version': '0.1',
    'category': 'Hidden',
    'description': """
        This bridge module allows to manage subcontracting with the purchase module.
    """,
    'depends': ['purchase_stock', 'mrp_subcontracting'],
    'data': [
        'views/supplier_info_views.xml',
    ],
    'installable': True,
    'auto_install': True,
}
