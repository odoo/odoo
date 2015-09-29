# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Margins by Products',
    'version': '1.0',
    'category': 'Sales Management',
    'description': """
Adds a reporting menu in products that computes sales, purchases, margins and other interesting indicators based on invoices.
=============================================================================================================================

The wizard to launch the report has several options to help you get the data you need.
""",
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/product_margin_view.xml',
        'product_margin_view.xml'
    ],
    'test':['test/product_margin.yml'],
    'demo': [],
    'installable': True,
    'auto_install': False,
}
