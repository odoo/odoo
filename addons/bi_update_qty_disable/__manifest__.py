# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
    "name": "Disable Update Quantity Feature",
    "version": "16.0.0.0",
    "category": "Warehouse",
    'summary': 'Disabling the update quantity feature on product disable update product quantity feature hide update product quantity feature disable update quantity feature on warehouse update stock hide update stock button disable update stock button disable update qty',
    "description": """The "Disable Update Quantity Feature Odoo App" helps users to prevent unauthorized modifications to the quantity of product. This app provides a simple solution for disabling the update quantity feature for certain users in Odoo, Currently in odoo multiple users have access to update the quantity of products, this app provides an effective way to prevent every users from updating the product quantity, Allowed users can only update quantity for products.""",
    'author': 'BrowseInfo',
    'website': 'https://www.browseinfo.com',
    "depends": ["stock"],
    "data": [
        'security/product_security.xml',
        'views/product.xml',
    ],
    "license":"OPL-1",
    "installable": True,
    "application": True,
    "auto_install": False,
    'live_test_url': 'https://youtu.be/xULqOoLTgaA',
    "images": ['static/description/Banner.gif'],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
