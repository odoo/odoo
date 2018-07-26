# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Products & Pricelists',
    'version': '1.2',
    'category': 'Sales',
    'depends': ['base', 'decimal_precision', 'mail', 'report'],
    'demo': [
        'product_demo.xml',
        'product_image_demo.xml',
    ],
    'description': """
This is the base module for managing products and pricelists in OpenERP.
========================================================================

Products support variants, different pricing methods, vendors information,
make to stock/order, different unit of measures, packaging and properties.

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
        'wizard/product_price_view.xml',
        'res_config_view.xml',
        'product_data.xml',
        'product_report.xml',
        'product_view.xml',
        'pricelist_view.xml',
        'partner_view.xml',
        'views/report_pricelist.xml',
        'views/report_productlabel.xml'
    ],
    'test': [
        'product_pricelist_demo.yml',
        'test/product_pricelist.yml',
    ],
    'installable': True,
    'auto_install': False,
}
