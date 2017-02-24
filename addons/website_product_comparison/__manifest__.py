# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Product Comparison And Product Attribute Category',
    'description': 'Product Comparison, Product Attribute Category and specification table',
    'author': 'Odoo SA',
    'website': 'https://www.odoo.com',
    'category': 'Website',
    'version': '1.0',
    'depends': ['website_sale'],
    'data': [
        'views/product_comparison_template.xml',
        'views/product_comparison_view.xml',
        'security/ir.model.access.csv',
        'security/product_comparison_security.xml',
    ],
    'demo': [
        'data/product_comparison_data.xml',
        'data/product_comparison_demo.xml',
    ],
    'installable': True,
}
