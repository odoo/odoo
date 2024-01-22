# Copyright 2023 Moduon Team S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

{
    "name": "Web Touchscreen",
    "summary": "UX improvements for touch screens",
    "version": "16.0.1.0.1",
    "development_status": "Alpha",
    "category": "Extra Tools",
    "website": "https://github.com/OCA/web",
    "author": "Moduon, Odoo Community Association (OCA)",
    "maintainers": ["yajo", "rafaelbn"],
    "license": "LGPL-3",
    "application": False,
    "installable": True,
    "depends": ["web"],
    "assets": {
        "web.assets_backend": [
            "web_touchscreen/static/src/**/*",
        ],
    },
}
