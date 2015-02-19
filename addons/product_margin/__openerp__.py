# -*- coding: utf-8 -*-

{
    'name': 'Margins by Products',
    'version': '1.0',
    'category': 'Sales Management',
    'website': 'https://www.odoo.com',
    'description': """
Adds a reporting menu in products that computes sales, purchases, margins and other interesting indicators based on invoices.
=============================================================================================================================

The wizard to launch the report has several options to help you get the data you need.
""",
    'author': 'Odoo S.A.',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/product_margin_view.xml',
        'views/product_margin_view.xml'
    ],
    'installable': True,
}
