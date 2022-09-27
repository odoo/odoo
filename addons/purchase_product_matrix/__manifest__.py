# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Purchase Matrix",
    'summary': """
       Add variants to your purchase orders through an Order Grid Entry.
    """,
    'description': """
        This module allows to fill Purchase Orders rapidly
        by choosing product variants quantity through a Grid Entry.
    """,
    'category': 'Inventory/Purchase',
    'version': '1.0',
    'depends': ['purchase', 'product_matrix'],
    'data': [
        'views/purchase_views.xml',
        'report/purchase_quotation_templates.xml',
        'report/purchase_order_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'purchase_product_matrix/static/src/**/*',
        ],
        'web.assets_tests': [
            'purchase_product_matrix/static/tests/tours/**/*',
        ],
    },
    'license': 'LGPL-3',
}
