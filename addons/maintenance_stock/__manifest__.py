{
    "name": "Maintenance - Inventory",
    "version": "1.0",
    "category": "Hidden",
    "summary": "Send equipment out for maintenance and receive it back, consume parts from stock, and receive the part a replacement took out",
    "author": "AgroMarin",
    "license": "LGPL-3",
    "depends": [
        "maintenance",
        "resource_asset_stock",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/stock_warehouse_views.xml",
        "views/stock_picking_views.xml",
        "views/resource_asset_part_views.xml",
        "views/maintenance_order_views.xml",
        "views/maintenance_order_transfer_views.xml",
        "wizards/maintenance_transfer_wizard_views.xml",
    ],
    "auto_install": True,
    "post_init_hook": "_create_warehouse_data",
}
