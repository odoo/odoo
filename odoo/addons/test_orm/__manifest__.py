{
    "name": "Test ORM",
    "version": "1.0",
    "category": "Hidden/Tests",
    "description": "A module to test the ORM.",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "base",
        "web",
        "web_tour",
    ],
    "data": [
        "security/ir.access.csv",
        "views/test_orm_views.xml",
        "data/test_orm_data.xml",
        "views/test_orm_menus.xml",
    ],
    "assets": {
        "web.assets_tests": [
            "test_orm/static/tests/tours/constraint.js",
            "test_orm/static/tests/tours/x2many.js",
        ],
    },
}
