{
    "name": "POS order workflow",
    "summary": "Modify the POS workflow to validate orders before payment and manage stock pickings.",
    "description": """ 
        This module customizes the standard POS workflow in Odoo 18 by introducing order validation before payment.
        Features:
        - Adds a "Send To Pick" button in the POS interface which allows users to select a shipping date before finalizing the order.
        - Creates a POS order and stock picking before payment.
        - Sets POS order status to "Ready".
        This enhancement ensures better order management, flexibility in processing payments, and accurate stock handling. """,
    "depends": ["point_of_sale"],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_order/static/src/*",
        ],
    },
    "auto_install": True,
    "license": "LGPL-3",
}
