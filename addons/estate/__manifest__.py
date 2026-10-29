# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Real Estate",
    "summary": "Advertise properties and manage the offers made on them",
    "description": """
Training addon of the Server framework 101 tutorial: property advertisements, offers, and the sale
of a property to the buyer whose offer was accepted.
""",
    "category": "Real Estate/Brokerage",
    "depends": ["base"],
    # Data files are loaded in this order: a record can only refer to records loaded before it
    "data": [
        "security/ir.access.csv",
        "views/estate_property_views.xml",
        "views/estate_property_offer_views.xml",
        "views/estate_property_type_views.xml",
        "views/estate_property_tag_views.xml",
        "views/estate_menus.xml",
        "views/res_users_views.xml",
    ],
    # Without this flag the addon would only be listed with the "Extra" filter of the Apps menu
    "application": True,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
