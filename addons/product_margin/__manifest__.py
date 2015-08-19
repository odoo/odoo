# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Margins by Products',
    'category': 'Sales',
    'description': """
Provides an option in products that computes sales, purchases, margins and other interesting indicators based on invoices.
""",
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'report/report_product_margin_views.xml',
        'views/product_views.xml',
    ],
}
