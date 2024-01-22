# Copyright 2019-2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Widget Open on new Tab",
    "summary": """
        Allow to open record from trees on new tab from tree views""",
    "version": "16.0.2.0.0",
    "license": "AGPL-3",
    "author": "Creu Blanca,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/web",
    "depends": ["web"],
    "demo": ["demo/res_users_view.xml"],
    "data": [
        "views/ir_model_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "web_widget_open_tab/static/src/xml/open_tab_widget.xml",
            "web_widget_open_tab/static/src/js/open_tab_widget.esm.js",
        ],
    },
}
