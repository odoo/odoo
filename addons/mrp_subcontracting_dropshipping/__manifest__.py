{
    "name": "Dropship and Subcontracting Management",
    "version": "0.2",
    "category": "Supply Chain/Purchase",
    "description": """
This bridge module allows to manage subcontracting with the dropshipping module.
    """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "mrp_subcontracting",
        "stock_dropshipping",
    ],
    "data": [
        "security/ir.access.csv",
        "data/mrp_subcontracting_dropshipping_data.xml",
        "views/purchase_order_views.xml",
    ],
    "auto_install": True,
}
