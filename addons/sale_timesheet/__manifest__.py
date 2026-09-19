{
    "name": "Sales Timesheet",
    "version": "1.1",
    "category": "Sales/Sales",
    "summary": "Sell based on timesheets",
    "description": """
Allows to sell timesheets in your sales order
=============================================

This module set the right product on all timesheet lines
according to the order/contract you work on. This allows to
have real delivered quantities in sales orders.
""",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "sale_project",
        "hr_timesheet",
    ],
    "data": [
        "data/sale_service_data.xml",
        "security/ir.model.access.csv",
        "security/sale_timesheet_security.xml",
        "views/account_invoice_views.xml",
        "views/sale_order_views.xml",
        "views/product_views.xml",
        "views/project_task_views.xml",
        "views/hr_timesheet_views.xml",
        "views/res_config_settings_views.xml",
        "views/sale_timesheet_portal_templates.xml",
        "views/project_sharing_views.xml",
        "views/project_portal_templates.xml",
        "reports/timesheets_analysis_views.xml",
        "reports/report_timesheet_templates.xml",
        "reports/project_report_view.xml",
        "wizards/sale_make_invoice_advance_views.xml",
        "views/sale_timesheet_menus.xml",
    ],
    "demo": [
        "demo/sale_service_demo.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "sale_timesheet/static/src/scss/sale_timesheet_portal.scss",
        ],
        "web.assets_backend": [
            "sale_timesheet/static/src/components/**/*",
        ],
        "web.assets_tests": [
            "sale_timesheet/static/tests/tours/**/*",
        ],
        "web.assets_unit_tests": [
            "sale_timesheet/static/tests/**/*",
            (
                "remove",
                "sale_timesheet/static/tests/tours/**/*",
            ),
        ],
        "project.webclient": [
            "sale_timesheet/static/src/components/so_line_field/*",
        ],
    },
    "auto_install": True,
    "post_init_hook": "_sale_timesheet_post_init",
    "uninstall_hook": "uninstall_hook",
}
