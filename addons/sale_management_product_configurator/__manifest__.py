# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Sale Management Product Configurator",
    'version': '1.0',
    'category': 'Hidden',
    'summary': "",
    'description': """""",
    'depends': ['sale_management', 'sale_product_configurator'],
    'data': [],
    'demo': [],
    'assets': {
        'web.assets_tests': [
            'sale_management_product_configurator/static/tests/tours/**/*',
        ],
    },
    'auto_install': True,
    'license': 'LGPL-3',
}
