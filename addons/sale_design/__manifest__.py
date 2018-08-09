# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Online Proposals',
    'category': 'Website',
    'summary': 'Sales',
    'website': 'https://www.odoo.com/page/quote-builder',
    'version': '1.0',
    'description': "",
    'depends': ['website', 'sale_management', 'website_mail'],
    'data': [
        'data/sale_design_data.xml',
        'views/sale_order_template.xml',
        'views/sale_quote_views.xml',
        'views/sale_order_views.xml',
    ],
    'demo': [
    ],
    'installable': True,
}
