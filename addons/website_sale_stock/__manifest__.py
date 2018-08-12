# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website Sale Stock - Website Delivery Information',
    'category': 'Technical Settings',
    'description': "",
    'depends': [
        'website_sale',
        'sale_stock',
    ],
    'auto_install': True,
    'data': [
        'views/product_template_views.xml',
        'views/res_config_settings_views.xml',
        'views/website_sale_stock_templates.xml',
        'views/stock_picking_views.xml'
    ],
    'demo': [
        'data/website_sale_stock_demo.xml',
    ],
}
