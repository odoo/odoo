{
    "name": "Events Sales",
    "version": "1.4",
    "category": "Marketing/Events",
    "description": """
Creating registration with sales orders.
========================================

This module allows you to automate and connect your registration creation with
your main sale flow and therefore, to enable the invoicing feature of registrations.

It defines a new kind of service products that offers you the possibility to
choose an event category associated with it. When you encode a sales order for
that product, you will be able to choose an existing event of that category and
when you confirm your sales order it will automatically create a registration for
this event.
""",
    "author": "Odoo S.A.",
    "website": "https://www.odoo.com/app/events",
    "license": "LGPL-3",
    "depends": [
        "event_product",
        "sale",
        "sale_team",
    ],
    "data": [
        "views/event_registration_views.xml",
        "views/event_views.xml",
        "views/product_template_views.xml",
        "views/sale_order_views.xml",
        "data/event_sale_data.xml",
        "data/mail_templates.xml",
        "reports/event_sale_report_views.xml",
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "security/event_security.xml",
        "wizards/event_edit_registration.xml",
        "wizards/event_configurator_views.xml",
        "views/event_sale_menus.xml",
    ],
    "demo": [
        "demo/event_sale_demo.xml",
        "demo/event_registration_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "event_sale/static/src/**/*",
        ],
        "web.assets_tests": [
            "event_sale/static/tests/tours/**/*",
        ],
    },
    "auto_install": True,
}
