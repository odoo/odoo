# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Products & Pricelists',
    'version': '1.2',
    'category': 'Sales Management',
    'depends': ['base', 'decimal_precision', 'mail', 'report'],
    'demo': [
        'data/product_demo.xml',
        'data/product_image_demo.xml',
    ],
    'description': """
This is the base module for managing products and pricelists in Odoo.
========================================================================

Products support variants, different pricing methods, vendors information,
make to stock/order, different units of measure, packaging and properties.

Pricelists support:
-------------------
    * Multiple-level of discount (by product, category, quantities)
    * Compute price based on different criteria:
        * Other pricelist
        * Cost price
        * List price
        * Vendor price

Pricelists preferences by product and/or partners.

Print product labels with barcode.
    """,
    'data': [
        'security/product_security.xml',
        'security/ir.model.access.csv',
        'data/product_data.xml',
        'views/res_config_views.xml',
        'report/product_report.xml',
        'views/product_views.xml',
        'views/pricelist_views.xml',
        'views/partner_views.xml',
        'views/pricelist_report.xml',
        'views/productlabel_report.xml',
        'wizard/product_price_views.xml'
    ]
}
