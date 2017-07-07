# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Products & Pricelists',
    'version': '1.2',
    'category': 'Sales',
    'depends': ['base', 'decimal_precision', 'mail'],
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
        'data/product_data.xml',
        'security/product_security.xml',
        'security/ir.model.access.csv',
        'wizard/product_price_list_views.xml',
        'views/res_config_settings_views.xml',
        'views/product_attribute_views.xml',
        'views/product_uom_views.xml',
        'views/product_views.xml',
        'views/product_template_views.xml',
        'views/product_pricelist_views.xml',
        'views/res_partner_views.xml',
        'views/product_template_import_templates.xml',
        'report/product_reports.xml',
        'report/product_pricelist_templates.xml',
        'report/product_product_templates.xml',
        'report/product_template_templates.xml',
    ],
    'demo': [
        'data/product_demo.xml',
        'data/product_image_demo.xml',
    ],
    'installable': True,
    'auto_install': False,
}
