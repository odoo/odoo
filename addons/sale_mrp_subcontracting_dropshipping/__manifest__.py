# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Sale Dropship and Subcontracting Management',
    'version': '0.1',
    'category': 'Hidden',
    'description': """
        This bridge module allows to manage sale orders with the subcontracting dropshipping module.
    """,
    'depends': ['mrp_subcontracting_dropshipping', 'sale'],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
