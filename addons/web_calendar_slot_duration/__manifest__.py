# Copyright 2021 Tecnativa - Jairo Llopis
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
{
    "name": "Calendar slot duration",
    "summary": "Customizable calendar slot durations",
    "version": "16.0.1.0.1",
    "development_status": "Production/Stable",
    "category": "Extra Tools",
    "website": "https://github.com/OCA/web",
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "maintainers": ["Yajo"],
    "license": "LGPL-3",
    "application": False,
    "installable": True,
    "assets": {
        "web.assets_backend": [
            "web_calendar_slot_duration/static/src/js/calendar_common_renderer.esm.js",
            "web_calendar_slot_duration/static/src/js/calendar_model.esm.js",
        ]
    },
    "depends": ["web"],
}
