# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': '3rd Party Tax Calculation for Sale',
    'description': '''
3rd Party Tax Calculation for Sale
==================================

Provides a common interface to be used when implementing apps to outsource tax calculation.
    ''',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'depends': ['account_external_tax', 'sale'],
    'auto_install': True,
    'data': [
        'views/sale_order_views.xml',
    ],
    'assets': {
        'web.assets_tests': [
            'sale_external_tax/static/tests/tours/sale_external_optional_products.js',
        ],
    },
    'license': 'OEEL-1',
}
