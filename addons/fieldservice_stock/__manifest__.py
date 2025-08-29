# Copyright (C) 2018 Brian McMaster
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Field Service - Stock",
    "summary": "Integrate the logistics operations with Field Service",
    "version": "18.0.1.0.0",
    "category": "Field Service",
    "author": "Open Source Integrators, "
    "Brian McMaster, "
    "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/field-service",
    "depends": ["fieldservice", "stock"],
    "data": [
        "security/ir.model.access.csv",
        "data/fsm_stock_data.xml",
        "views/res_territory.xml",
        "views/fsm_location.xml",
        "views/fsm_order.xml",
        "views/stock.xml",
        "views/stock_picking.xml",
    ],
    "pre_init_hook": "_pre_init_hook",
    "license": "AGPL-3",
    "development_status": "Beta",
    "maintainers": ["brian10048", "wolfhall", "max3903", "smangukiya"],
}
