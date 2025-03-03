{
    "name": "POS Improvement",
    "version": "1.0",
    "summary": "POS Improvement",
    "description": """
        Show payment button in order page of POS module for unpaid orders
    """,
    "author": "Odoo",
    "license": "LGPL-3",
    "depends": ["point_of_sale"],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_improvement/static/src/**/*",
        ],
    },
}
