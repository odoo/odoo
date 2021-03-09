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
            # after script[last()]
            'purchase_product_matrix/static/src/js/product_matrix_configurator.js',
        ],
        'web.qunit_suite_tests': [
            # inside .
            'purchase_product_matrix/static/tests/section_and_note_widget_tests.js',
        ],
        'web.assets_tests': [
            # inside .
            'purchase_product_matrix/static/tests/tours/purchase_product_matrix_tour.js',
        ],
    }
}
