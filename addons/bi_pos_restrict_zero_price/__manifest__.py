# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Restrict POS Order Line with Zero Price',
    'version': '16.0.0.0',
    'category': 'Point of Sale',
    'summary': 'Point of sale restrict zero pos restrict negative price point of sales with zero price pos zero price restriction product point of sale negative price restriction pos order line restriction with zero price restrict zero price order line from pos',
    'description': """
       
       Restrict POS Order Line with Zero Price app helps users to prevents the sales of products with zero or negative price. User have option to enable or disable restrict zero price order line from POS configuration. Display warning/validation message, If user tries to select product which has zero price in point of sale order line.
    
    """,
    'author': 'BrowseInfo',
    'website': 'https://www.browseinfo.com',
    'depends': ['base', 'point_of_sale'],
    'data': [
        'views/pos_config_view.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            'bi_pos_restrict_zero_price/static/src/js/product_screen.js',
        ],
    },
    'license':'OPL-1',
    'installable': True,
    'auto_install': False,
    'live_test_url':'https://youtu.be/jnJbNboz2cY',
    "images":['static/description/POS-Order-Line-Restrict-Zero-Price-Banner.gif'],
}
