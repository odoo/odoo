{
    "name": "pos_mrp",
    "version": "1.0",
    "category": "Sales/Point of Sale",
    "sequence": 6,
    "summary": "Link module between Point of Sale and Mrp",
    "description": """
This is a link module between Point of Sale and Mrp.
""",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "point_of_sale",
        "mrp",
    ],
    "data": [
        "security/ir.access.csv",
    ],
    "assets": {
        "web.assets_tests": [
            "pos_mrp/static/tests/tours/**/*",
        ],
    },
    "auto_install": True,
}
