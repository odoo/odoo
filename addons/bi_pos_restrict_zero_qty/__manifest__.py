# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
{
    'name': 'POS Restrict Zero Quantity',
    'version': '19.0.0.0',
    'category': 'Point of Sale',
    'summary': 'Point Of Sale Restrict Zero Quantity pos restrict negative stock sales of products with zero or negative stock levels pos restrict zero stock product pos Restrict product with zero Quantity pos order line restriction with zero Quantity on pos',
    'description' :"""
       The Point Of Sale Restrict Zero Quantity Odoo App helps users to prevents the sales of products with zero or negative stock levels, ensuring that businesses never run out of stock. Additionally, the app can be configured to display a warning message when the stock level of a product is getting low. When a customer attempts to purchase a product with a stock level below the minimum, the app will display an error message, preventing the sale from going through.
    """,
    'author': 'BROWSEINFO',
    'website': 'https://www.browseinfo.com/demo-request?app=bi_pos_restrict_zero_qty&version=19&edition=Community',
    'depends': ['base','point_of_sale'],
    'data': [
        'views/pos_config_view.xml',
    ],
    'assets':{
        'point_of_sale._assets_pos': [
            '/bi_pos_restrict_zero_qty/static/src/app/models/models.js',
         ],
    },
    'demo': [],
    'test': [],
    'license':'OPL-1',
    'installable': True,
    'auto_install': False,
    'live_test_url':'https://www.browseinfo.com/demo-request?app=bi_pos_restrict_zero_qty&version=19&edition=Community',
    "images":['static/description/Banner.gif'],
}
