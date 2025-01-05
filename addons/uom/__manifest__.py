# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Units of measure',
    'version': '1.0',
    'category': 'Sales/Sales',
    'depends': ['base'],
    'description': """
This is the base module for managing Units of measure.
========================================================================
    """,
    'data': [
        'data/uom_data.xml',
        'security/uom_security.xml',
        'security/ir.model.access.csv',
        'views/uom_uom_views.xml',
    ],
    'installable': True,
    'assets': {
        'web.assets_backend': [
            'uom/static/src/components/**/*',
        ],
    },
    'license': 'LGPL-3',
}
