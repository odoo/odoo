# Copyright (C) 2022 - Today: GRAP (http://www.grap.coop)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Web Theme Classic",
    "summary": "Contrasted style on fields to improve the UI.",
    "version": "16.0.1.0.2",
    "author": "GRAP, Odoo Community Association (OCA)",
    "maintainers": ["legalsylvain"],
    "website": "https://github.com/OCA/web",
    "license": "AGPL-3",
    "category": "Extra Tools",
    "depends": [
        "web",
    ],
    "assets": {
        "web.assets_backend": [
            "/web_theme_classic/static/src/scss/web_theme_classic.scss",
        ],
    },
    "installable": True,
    "application": True,
}
