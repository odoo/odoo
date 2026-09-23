{
    "name": "Purchase Requisition Stock",
    "version": "1.3",
    "category": "Supply Chain/Purchase",
    "sequence": 70,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "purchase_requisition",
        "purchase_stock",
    ],
    "data": [
        "security/ir.access.csv",
        "data/purchase_requisition_stock_data.xml",
        "views/purchase_views.xml",
        "views/purchase_requisition_views.xml",
    ],
    "auto_install": True,
}
