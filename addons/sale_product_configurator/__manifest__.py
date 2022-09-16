# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Sale Product Configurator",
    'version': '1.0',
    'category': 'Hidden',
    'summary': "Configure your products",

    'description': """
Technical module:
The main purpose is to override the sale_order view to allow configuring products in the SO form.

It also enables the "optional products" feature.
    """,

    'depends': ['sale'],
    'data': [
        'views/product_template_views.xml',
        'views/sale_order_views.xml',
        'views/templates.xml',
    ],
    'demo': [
        'data/sale_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'sale/static/src/js/variant_mixin.js',
            'sale_product_configurator/static/src/js/product_configurator_widget.js',
            'sale_product_configurator/static/src/js/product_configurator_modal.js',
        ],
        'web.qunit_suite_tests': [
            'sale_product_configurator/static/tests/product_configurator.test.js',
        ],
    },
    'auto_install': True,
    'license': 'LGPL-3',
}
