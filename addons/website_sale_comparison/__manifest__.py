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
        'security/ir.model.access.csv',
        'views/website_sale_comparison_template.xml',
        'views/website_sale_comparison_view.xml',
    ],
    'demo': [
        'data/website_sale_comparison_data.xml',
        'data/website_sale_comparison_demo.xml',
    ],
    'installable': True,
}
