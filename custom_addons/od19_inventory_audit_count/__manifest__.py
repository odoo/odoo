{
    "name": "OD19 Inventory Audit Count",
    "version": "19.0.1.0.0",
    "author": "TRAE",
    "depends": ["stock", "od19_inventory_execution_control"],
    "data": [
        "security/ir.model.access.csv",
        "views/stock_count_session_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
    "icon": "/od19_inventory_audit_count/static/description/icon.svg",
}
