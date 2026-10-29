# Copyright (C) 2011 Julius Network Solutions SARL <contact@julius.fr>
# Copyright 2018 Camptocamp SA
# Copyright 2020 Tecnativa - João Marques
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

{
    "name": "Move Stock Location",
    "version": "16.0.1.4.0",
    "author": "Julius Network Solutions, "
    "BCIM,"
    "Camptocamp,"
    "Odoo Community Association (OCA)",
    "summary": "This module allows to move all stock "
    "in a stock location to an other one.",
    "website": "https://github.com/OCA/stock-logistics-warehouse",
    "license": "AGPL-3",
    "depends": ["stock"],
    "category": "Stock",
    "data": [
        "data/stock_quant_view.xml",
        "security/ir.model.access.csv",
        "views/stock_picking_type_views.xml",
        "views/stock_picking.xml",
        "wizard/stock_move_location.xml",
    ],
    "post_init_hook": "enable_multi_locations",
}
