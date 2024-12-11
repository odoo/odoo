# Copyright 2021 VentorTech OU
# Part of Ventor modules. See LICENSE file for full copyright and licensing details.

{
    'name': 'Product Multiple Barcodes',
    "version": "17.0.1.0.0",
    'author': 'VentorTech',
    'website': 'https://ventor.tech/',
    'license': 'LGPL-3',
    'installable': True,
    'images': ['static/description/main_banner.png'],
    'summary': 'Allows to define multiple additional barcodes for products and to search products by additional barcodes and internal reference.',
    'depends': [
        'product',
        'sale',
        'stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/multiply_barcode_wizard.xml',
        'views/product_template_views.xml',
        'views/stock_picking_views.xml',
    ],
}
