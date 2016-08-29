# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Portal Stock',
    'version': '0.1',
    'category': 'Warehouse',
    'complexity': 'easy',
    'description': """
This module adds access rules to your portal if stock and portal are installed.
==========================================================================================
    """,
    'depends': ['sale_stock','portal'],
    'data': [
        'security/portal_security.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': True,
    'category': 'Hidden',
}
