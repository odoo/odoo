# Copyright 2015 ACSONE SA/NV
# Copyright 2018 Amaris
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Web Dialog Size",
    "summary": """
        A module that lets the user expand a
        dialog box to the full screen width.""",
    "author": "ACSONE SA/NV, "
    "Therp BV, "
    "Siddharth Bhalgami,"
    "Tecnativa, "
    "Amaris, "
    "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/web",
    "category": "web",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "depends": ["web"],
    "installable": True,
    "assets": {
        "web.assets_backend": [
            "/web_dialog_size/static/src/js/web_dialog_size.js",
            "/web_dialog_size/static/src/js/web_dialog_size.esm.js",
            "/web_dialog_size/static/src/js/web_dialog_draggable.esm.js",
            "/web_dialog_size/static/src/scss/web_dialog_size.scss",
            "/web_dialog_size/static/src/xml/web_dialog_size.xml",
            "/web_dialog_size/static/src/xml/ExpandButton.xml",
            "/web_dialog_size/static/src/xml/DialogDraggable.xml",
        ],
    },
}
