# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'MRP Subcontracting Quality',
    'version': '1.0',
    'category': 'Manufacturing/Quality',
    'description': """
Bridge module between MRP subcontracting and Quality
    """,
    'depends': [
        'mrp_subcontracting', 'quality_control'
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}
