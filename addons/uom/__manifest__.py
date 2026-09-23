{
    "name": "Units of measure",
    "version": "1.2",
    "category": "Sales/Sales",
    "description": """
This is the base module for managing Units of measure.
========================================================================
    """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "base",
        "web",
    ],
    "data": [
        "data/uom_data.xml",
        "security/uom_security.xml",
        "security/ir.access.csv",
        "views/uom_uom_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "uom/static/src/components/**/*",
        ],
        "web.assets_unit_tests": [
            "uom/static/tests/**/*",
        ],
    },
}
