# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Sale Product Configurator",
    'version': '1.0',
    'category': 'Hidden',
    'summary': "Configure your products",

    'description': """
Technical module installed when the user checks the "module_sale_product_configurator" setting.
The main purpose is to override the sale_order view to allow configuring products in the SO form.

It also enables the "optional products" feature.
    """,

    'depends': ['sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/templates.xml',
        'views/sale_views.xml',
        'wizard/sale_product_configurator_views.xml',
    ],
    'demo': [
        'data/sale_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # after script[last()]
            'sale/static/src/js/variant_mixin.js',
            # after script[last()]
            'sale_product_configurator/static/src/js/product_configurator_renderer.js',
            # after script[last()]
            'sale_product_configurator/static/src/js/product_configurator_controller.js',
            # after script[last()]
            'sale_product_configurator/static/src/js/product_configurator_view.js',
            # after script[last()]
            'sale_product_configurator/static/src/js/product_configurator_widget.js',
            # after script[last()]
            'sale_product_configurator/static/src/js/product_configurator_modal.js',
        ],
        'web.assets_tests': [
            # inside .
            'sale_product_configurator/static/tests/tours/product_configurator_ui.js',
            # inside .
            'sale_product_configurator/static/tests/tours/product_configurator_advanced_ui.js',
            # inside .
            'sale_product_configurator/static/tests/tours/product_configurator_edition_ui.js',
            # inside .
            'sale_product_configurator/static/tests/tours/product_configurator_single_custom_attribute_ui.js',
            # inside .
            'sale_product_configurator/static/tests/tours/product_configurator_pricelist_ui.js',
            # inside .
            'sale_product_configurator/static/tests/tours/product_configurator_optional_products_ui.js',
        ],
        'web.qunit_suite_tests': [
            # inside .
            'sale_product_configurator/static/tests/product_configurator.test.js',
        ],
    }
}
