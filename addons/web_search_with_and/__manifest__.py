# Copyright 2015 Andrius Preimantas <andrius@versada.lt>
# Copyright 2020 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Use AND conditions on omnibar search",
    "version": "16.0.1.0.0",
    "author": """Sandip SCS, Versada UAB, ACSONE SA/NV, Serincloud,
    Odoo Community Association (OCA)""",
    "license": "AGPL-3",
    "category": "web",
    "website": "https://github.com/OCA/web",
    "depends": ["web"],
    "assets": {
        "web.assets_backend": [
            "/web_search_with_and/static/src/js/search_model.esm.js",
            "/web_search_with_and/static/src/js/search_bar.esm.js",
        ],
    },
}
