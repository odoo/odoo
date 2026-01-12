# Copyright 2016-2024 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


{
    "name": "Sessions in Redis",
    "summary": "Store web sessions in Redis",
    "version": "19.0.1.0.0",
    "author": "Camptocamp,Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "category": "Extra Tools",
    "depends": ["base"],
    "excludes": [
        # OCA/server-auth
        "auth_session_timeout",
    ],
    "external_dependencies": {
        "python": ["redis"],
    },
    "website": "https://github.com/camptocamp/odoo-cloud-platform",
    "installable": True,
}
