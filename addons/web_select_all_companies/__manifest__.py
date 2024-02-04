# Copyright 2023 Camptocamp SA - Telmo Santos
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

{
    "name": "Web Select All Companies",
    "summary": "Allows you to select all companies in one click.",
    "version": "16.0.1.0.1",
    "category": "Web",
    "website": "https://github.com/OCA/web",
    "author": "Camptocamp, Odoo Community Association (OCA)",
    "license": "LGPL-3",
    "depends": ["web"],
    "assets": {
        "web.assets_backend": [
            "web_select_all_companies/static/src/scss/switch_all_company_menu.scss",
            "web_select_all_companies/static/src/xml/switch_all_company_menu.xml",
            "web_select_all_companies/static/src/js/switch_all_company_menu.esm.js",
        ],
    },
    "installable": True,
}
