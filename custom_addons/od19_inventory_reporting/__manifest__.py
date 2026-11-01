{
    "name": "OD19 Inventory Reporting",
    "author": "OD19",
    "version": "19.0.2.0.0",
    "depends": [
        "stock",
        "stock_landed_costs",
        "od19_inventory_execution_control",
        "od19_inventory_audit_count",
        "od19_goods_issue",
        "od19_dashboard",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/report_inventory_movement_backlog_views.xml",
        "views/report_inventory_accuracy_views.xml",
        "data/logistics_dashboard_data.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
    "icon": "/od19_inventory_reporting/static/description/icon.svg",
}
