# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Products & Pricelists',
    'version': '1.2',
    'category': 'Sales/Sales',
    'depends': ['base', 'mail', 'uom'],
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

        'wizard/product_label_layout_views.xml',

        'views/product_views.xml',

        'views/res_config_settings_views.xml',
        'views/product_attribute_views.xml',
        'views/product_category_views.xml',
        'views/product_packaging_views.xml',
        'views/product_pricelist_item_views.xml',
        'views/product_pricelist_views.xml',
        'views/product_supplierinfo_views.xml',
        'views/product_template_views.xml',
        'views/product_tag_views.xml',
        'views/res_country_group_views.xml',
        'views/res_partner_views.xml',

        'report/product_reports.xml',
        'report/product_product_templates.xml',
        'report/product_template_templates.xml',
        'report/product_packaging.xml',
        'report/product_pricelist_report_templates.xml',
    ],
    'demo': [
        'data/product_demo.xml',
    ],
    'installable': True,
    'assets': {
        'web.assets_backend': [
            'product/static/src/js/**/*',
            'product/static/src/xml/**/*',
        ],
        'web.report_assets_common': [
            'product/static/src/scss/report_label_sheet.scss',
        ],
        'web.qunit_suite_tests': [
            'product/static/tests/**/*',
        ],
    },
    'license': 'LGPL-3',
}
