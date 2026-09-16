# Copyright 2015-2016 Akretion - Alexis de Lattre
# Copyright 2016-2017 Tecnativa - Pedro M. Baeza
# Copyright 2018 Tecnativa - Ernesto Tejeda
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Partner External Maps",
    "version": "16.0.1.0.0",
    "category": "Extra Tools",
    "license": "AGPL-3",
    "summary": "Add Map and Map Routing buttons on partner form to "
    "open GMaps, OSM, Bing and others",
    "author": "Akretion, Tecnativa, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/partner-contact",
    "depends": ["base"],
    "data": [
        "views/res_partner_view.xml",
        "views/map_website_view.xml",
        "data/map_website_data.xml",
        "views/res_users_view.xml",
        "security/ir.model.access.csv",
    ],
    "post_init_hook": "set_default_map_settings",
    "installable": True,
}
