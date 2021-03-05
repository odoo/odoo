# -*- coding: utf-8 -*-
{
    'name': "Website Sale Stock Wishlist",
    'summary': """
        Bridge module for website_sale_stock and website_sale_wishlist""",
    'description': """
         Bridge module to advise shopper's to add product to their wishlist if stock is empty and wishlist enabled""",
    'category': 'Hidden',
    'version': '0.1',
    'auto_install': True,

    'depends': [
        'website_sale_stock',
        'website_sale_wishlist'
    ],
    'qweb': ['static/src/xml/add_to_wishlist_advice.xml'],

}
