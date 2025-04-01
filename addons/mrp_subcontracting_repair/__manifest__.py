# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'MRP Subcontracting Repair',
    'version': '1.0',
    'category': 'Manufacturing/Repair',
    'description': """
Bridge module between MRP subcontracting and Repair
    """,
    'depends': [
        'mrp_subcontracting', 'repair'
    ],
    'data': [
        'security/ir.access.csv',
    ],
    'installable': True,
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
