{
    "name": "OD19 Inventory Execution Control",
    "version": "19.0.1.0.0",
    "author": "TRAE",
    # Intentional Wave 1 integration baseline, not accidental over-coupling.
    "depends": [
        "stock",
        "purchase_stock",
        "sale_stock",
        "od19_purchase_procurement_core",
        "od19_sales_project_context",
        # Owns ``project.project.od19_project_type`` (NOT NULL). Without this
        # dependency our tests may run before the field is registered, and any
        # project creation would violate the not-null constraint.
        "od19_project_document_sequence",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/product_views.xml",
        "views/stock_picking_views.xml",
        "views/stock_valuation_by_lot_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
    "icon": "/od19_inventory_execution_control/static/description/icon.svg",
}
