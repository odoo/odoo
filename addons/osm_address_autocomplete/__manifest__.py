# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "OSM autocompletado",
    "summary": "Autocompletado de direcciones con OpenStreetMap",
    "version": "1.0",
    "author": "Contel - Convergencia de telecomunicaciones, S.L.",
    "category": "Tools",
    "depends": ["web", "crm"],
    "data": [
        "views/res_partner_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "osm_address_autocomplete/static/src/address_autocomplete/**/*.js",
            "osm_address_autocomplete/static/src/address_autocomplete/**/*.xml",
        ],
    },
    "license": "LGPL-3",
}
