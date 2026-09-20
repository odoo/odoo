{
    "name": "Products & Pricelists",
    "version": "1.10",
    "category": "Sales/Sales",
    "description": """
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
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "uom",
        "mail",
        "mixin_attribute",
    ],
    "data": [
        "data/product_data.xml",
        "data/product_uom_activate.xml",
        "security/product_security.xml",
        "security/ir.model.access.csv",
        "wizards/product_label_layout_views.xml",
        "wizards/product_merge_views.xml",
        "wizards/update_product_attribute_value_views.xml",
        "views/product_tag_views.xml",
        "views/product_template_views.xml",
        "views/product_views.xml",
        "views/res_config_settings_views.xml",
        "views/product_attribute_views.xml",
        "views/product_attribute_value_views.xml",
        "views/product_category_views.xml",
        "views/product_combo_views.xml",
        "views/product_pricelist_item_views.xml",
        "views/product_pricelist_views.xml",
        "views/product_supplierinfo_views.xml",
        "views/product_template_attribute_line_views.xml",
        "views/res_country_group_views.xml",
        "views/res_partner_views.xml",
        "views/uom_views.xml",
        "reports/product_reports.xml",
        "reports/product_product_templates.xml",
        "reports/product_template_templates.xml",
        "reports/product_packaging.xml",
        "reports/product_pricelist_report_templates.xml",
        "views/product_menu.xml",
    ],
    "demo": [
        "demo/product_attribute_demo.xml",
        "demo/product_category_demo.xml",
        "demo/product_demo.xml",
        "demo/product_supplierinfo_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "product/static/src/js/**/*",
            "product/static/src/product_catalog/**/*.js",
            "product/static/src/product_catalog/**/*.xml",
            "product/static/src/product_catalog/**/*.scss",
            "product/static/src/product_name_and_description/**/*.js",
            "product/static/src/scss/product_form.scss",
        ],
        "web.report_assets_common": [
            "product/static/src/scss/report_label_sheet.scss",
        ],
        "web.assets_unit_tests": [
            "product/static/tests/**/*",
        ],
    },
}
