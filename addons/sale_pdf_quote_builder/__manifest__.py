{
    "name": "Sales PDF Quotation Builder",
    "category": "Sales/Sales",
    "description": "Build nice quotations",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "document_product",
        "sale",
    ],
    "data": [
        "data/ir_cron.xml",
        "data/sale_pdf_form_field.xml",
        "reports/ir_actions_report.xml",
        "security/ir.model.access.csv",
        "security/ir_rules.xml",
        "views/product_document_views.xml",
        "views/quotation_document_views.xml",
        "views/sale_order_template_views.xml",
        "views/sale_order_views.xml",
        "views/sale_pdf_form_field_views.xml",
        "views/sale_pdf_quote_builder_menus.xml",
        "wizards/res_config_settings_views.xml",
    ],
    "demo": [
        "demo/sale_pdf_quote_builder_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "sale_pdf_quote_builder/static/src/js/**/*",
        ],
        "web.assets_tests": [
            "sale_pdf_quote_builder/static/tests/tours/**/*",
        ],
    },
    "auto_install": True,
}
