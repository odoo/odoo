# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Sale Product Configurators Tests",
    'summary': "Test Suite for Sale Product Configurator",
    'category': "Hidden",
    'depends': [
        'event_sale',
        'sale_management',
        'sale_product_configurator',
        'sale_product_matrix',
    ],
    'assets': {
        'web.assets_tests': [
            'test_sale_product_configurators/static/tests/tours/**/*',
        ],
    },
    'license': 'OEEL-1',
}
