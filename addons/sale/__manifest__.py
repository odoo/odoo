{
    "name": "Sales",
    "version": "1.9",
    "category": "Sales/Sales",
    "sequence": 5,
    "summary": "From quotations to invoices",
    "description": """
Manage sales quotations and orders
==================================

This application allows you to manage your sales goals in an effective and efficient manner by keeping track of all sales orders and history.

It handles the full sales workflow:

* **Quotation** -> **Sales order** -> **Invoice**

Preferences (only with Warehouse Management installed)
------------------------------------------------------

If you also installed the Warehouse Management, you can deal with the following preferences:

* Shipping: Choice of delivery at once or partial delivery
* Invoicing: choose how invoices will be paid
* Incoterms: International Commercial terms


With this module you can personnalize the sales order and invoice report with
categories, subtotals or page-breaks.

The Sales app can be hidden from the app launcher in the settings, for databases
that reach sales orders only through another application.
    """,
    "author": "Odoo S.A.",
    "website": "https://www.odoo.com/app/sales",
    "license": "LGPL-3",
    "depends": [
        "base_order",
        "mixin_report_sql",
        "document",
        "document_product",
        "account_payment_provider",
        "utm",
    ],
    "data": [
        "security/res_groups.xml",
        "security/ir.model.access.csv",
        "security/ir_rules.xml",
        "reports/ir_actions_report_templates.xml",
        "reports/ir_actions_report.xml",
        "reports/sale_report_views.xml",
        "reports/sale_invoice_match_views.xml",
        "reports/sale_invoice_line_match_views.xml",
        "data/ir_cron.xml",
        "data/ir_sequence_data.xml",
        "data/mail_message_subtype_data.xml",
        "data/mail_template_data.xml",
        "data/sale_tour.xml",
        "data/ir_config_parameter.xml",
        "data/digest_data.xml",
        "views/sale_order_template_views.xml",
        "wizards/account_accrued_orders_wizard_views.xml",
        "wizards/invoice_to_so_wizard_views.xml",
        "wizards/mass_cancel_orders_views.xml",
        "wizards/payment_link_wizard_views.xml",
        "wizards/res_config_settings_views.xml",
        "wizards/sale_make_invoice_advance_views.xml",
        "wizards/sale_order_discount_views.xml",
        "wizards/sale_order_line_price_history_views.xml",
        "views/sale_order_views.xml",
        "views/account_move_views.xml",
        "views/digest_digest_views.xml",
        "views/mail_activity_views.xml",
        "views/mail_activity_plan_views.xml",
        "views/payment_views.xml",
        "views/product_document_views.xml",
        "views/product_pricelist_item_views.xml",
        "views/product_template_views.xml",
        "views/product_product_views.xml",
        "views/res_partner_views.xml",
        "views/sale_order_line_views.xml",
        "views/sale_portal_templates.xml",
        "views/utm_campaign_views.xml",
        "views/sale_menus.xml",
    ],
    "demo": [
        "demo/product_demo.xml",
        "demo/sale_demo.xml",
        "demo/sale_order_template_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "sale/static/src/scss/sale_onboarding.scss",
            "sale/static/src/js/badge_extra_price/*",
            "sale/static/src/js/sale_action_helper/*",
            "sale/static/src/js/combo_configurator_dialog/*",
            "sale/static/src/js/models/*",
            "sale/static/src/js/product/*",
            "sale/static/src/js/product_card/*",
            "sale/static/src/js/product_configurator_dialog/*",
            "sale/static/src/js/product_list/*",
            "sale/static/src/js/product_template_attribute_line/*",
            "sale/static/src/js/quantity_buttons/*",
            "sale/static/src/js/sale_order_line_field/*",
            "sale/static/src/js/sale_order_template_line_field/*",
            "sale/static/src/js/section_optional_line_utils.js",
            "sale/static/src/js/tours/sale.js",
            "sale/static/src/js/upload_rfq_cog_menu/*",
            "sale/static/src/js/sale_product_field.js",
            "sale/static/src/js/sale_product_field.scss",
            "sale/static/src/js/sale_utils.js",
            "sale/static/src/xml/**/*",
            "sale/static/src/views/**/*",
        ],
        "web.assets_frontend": [
            "sale/static/src/interactions/**/*",
            "sale/static/src/scss/sale_portal.scss",
        ],
        "web.assets_tests": [
            "sale/static/tests/tours/**/*",
            "sale/static/src/js/tours/combo_configurator_tour_utils.js",
            "sale/static/src/js/tours/product_configurator_tour_utils.js",
            "sale/static/src/js/tours/tour_utils.js",
        ],
        "web.assets_unit_tests": [
            "sale/static/tests/mock_server/**/*",
            "sale/static/tests/sale_test_helpers.js",
            "sale/static/src/interactions/**/*",
            "sale/static/tests/**/*.test.js",
        ],
        "web.report_assets_common": [
            "sale/static/src/scss/sale_report.scss",
        ],
    },
    "application": True,
    "post_init_hook": "_post_init_hook",
}
