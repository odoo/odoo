# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Sale Matrix",
    'summary': "Add variants to Sales Order through a grid entry.",
    'description': """
        This module allows to fill Sales Order rapidly
        by choosing product variants quantity through a Grid Entry.
    """,
    'category': 'Sales/Sales',
    'version': '1.0',
    'depends': ['sale', 'product_matrix', 'sale_product_configurator'],
    'data': [
        'views/product_template_views.xml',
        'views/sale_views.xml',
        'report/sale_report_templates.xml',
    ],
    'demo': [
        'data/product_matrix_demo.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'sale_product_matrix/static/src/**/*',
        ],
        'web.qunit_suite_tests': [
            'sale_product_matrix/static/tests/section_and_note_widget_tests.js',
        ],
        'web.assets_tests': [
            'sale_product_matrix/static/tests/tours/**/*',
        ],
    },
    'license': 'LGPL-3',
}
