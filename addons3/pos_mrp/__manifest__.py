# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'pos_mrp',
    'version': '1.0',
    'category': 'Hidden',
    'sequence': 6,
    'summary': 'Link module between Point of Sale and Mrp',
    'description': """
This is a link module between Point of Sale and Mrp.
""",
    'depends': ['point_of_sale', 'mrp'],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
