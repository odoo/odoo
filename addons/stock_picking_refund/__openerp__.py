# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Decrease delivred quantity',
    'version': '1.0',
    'category': 'Stock',
    'description': """
This allows to decrease the quantity delivered in the
associated SO, and therefore to generate refunds more easily.
==============================================================
""",
    'depends': ['sale_stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_stock_view.xml',

    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}
