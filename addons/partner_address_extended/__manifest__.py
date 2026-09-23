{
    "name": "Extended Addresses",
    "version": "1.2",
    "category": "Sales/Sales",
    "sequence": 19,
    "summary": "Add extra fields on addresses",
    "description": """
Extended Addresses Management
=============================

This module provides the ability to choose a city from a list (in specific countries).

It is primarily used for EDIs that might need a special city code.
        """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "partner",
    ],
    "data": [
        "security/ir.access.csv",
        "views/partner_address_extended.xml",
        "views/res_city_view.xml",
        "views/res_country_view.xml",
        "views/partner_address_extended_menus.xml",
    ],
}
