# Copyright 2022 Hynsys Technologies
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "Chatter Position",
    "summary": "Add an option to change the chatter position",
    "version": "16.0.1.0.0",
    "author": "Hynsys Technologies, Camptocamp, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/web",
    "license": "LGPL-3",
    "category": "Extra Tools",
    "depends": ["web", "mail"],
    "data": ["views/res_users.xml", "views/web.xml"],
    "assets": {
        "web.assets_backend": [
            "/web_chatter_position/static/src/**/*.js",
        ],
    },
}
