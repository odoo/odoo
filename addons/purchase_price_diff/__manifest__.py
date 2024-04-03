# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'WMS Accounting',
    'version': '1.1',
    'summary': 'Inventory, Logistic, Valuation, Accounting',
    'description': """
WMS Accounting module
======================
This module adds the price difference account. Used in standard perpetual valuation.
    """,
    'depends': ['purchase_stock'],
    'data': [
        'views/product_views.xml',
    ],
    'category': 'Hidden',
    'sequence': 16,
    'auto_install': True,
    'license': 'LGPL-3',
}
