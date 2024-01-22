# Copyright 2016 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Web timeline",
    "summary": "Interactive visualization chart to show events in time",
    "version": "16.0.1.0.3",
    "development_status": "Production/Stable",
    "author": "ACSONE SA/NV, "
    "Tecnativa, "
    "Monk Software, "
    "Onestein, "
    "Trobz, "
    "Odoo Community Association (OCA)",
    "category": "web",
    "license": "AGPL-3",
    "website": "https://github.com/OCA/web",
    "depends": ["web"],
    "data": [],
    "maintainers": ["tarteo"],
    "application": False,
    "installable": True,
    "assets": {
        "web.assets_backend": [
            "web_timeline/static/src/scss/web_timeline.scss",
            "web_timeline/static/src/js/timeline_view.js",
            "web_timeline/static/src/js/timeline_renderer.js",
            "web_timeline/static/src/js/timeline_controller.esm.js",
            "web_timeline/static/src/js/timeline_model.js",
            "web_timeline/static/src/js/timeline_canvas.js",
            "web_timeline/static/src/xml/web_timeline.xml",
        ],
    },
}
