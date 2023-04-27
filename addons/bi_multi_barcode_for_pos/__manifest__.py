# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
    "name" : "POS Multi Barcodes-Product Multi Barcode for POS",
    "version" : "16.0.0.0",
    "category" : "Point of Sale",
    'summary': 'Product Multi Barcode for Product multiple barcode for product barcode search product based on barcode pos multiple barcode point of sale multi barcode for pos multi barcode for point of sales multi barcode for pos barcode pos product barcode for pos',
    "description": """
    
   User can add multiple barcodes to product and can find product useing any of barcode added to product on point of sale, User can also search product using multiple barcodes on product search view and also on sale, purchase, customer invoice, vendor bill, delivery order, and receipt.
    
    """,
    "author": "BrowseInfo",
    "website" : "https://www.browseinfo.in",
    "price": 10,
    "currency": 'EUR',
    "depends" : ['web','base', 'point_of_sale','bi_multi_barcode_for_product'],
    "data": [
    ],
    'assets': {
        'point_of_sale.assets': [
            "bi_multi_barcode_for_pos/static/src/js/barcode.js" ,
            "bi_multi_barcode_for_pos/static/src/js/ProductScreen.js" ,
        ],
    },

    "auto_install": False,
    "installable": True,
    "live_test_url":'https://youtu.be/OzvpyGWrJ1c',
    "images":["static/description/Banner.gif"],
    'license': 'OPL-1',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
