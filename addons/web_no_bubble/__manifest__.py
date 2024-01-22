# Copyright 2016 Savoir-faire Linux
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "Web No Bubble",
    "version": "16.0.1.0.0",
    "author": "Savoir-faire Linux, " "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/web",
    "license": "AGPL-3",
    "category": "Web",
    "summary": "Remove the bubbles from the web interface",
    "depends": ["web"],
    "installable": True,
    "application": False,
    "assets": {
        "web.assets_backend": ["web_no_bubble/static/src/css/web_no_bubble.scss"],
        "web.assets_frontend": ["web_no_bubble/static/src/css/web_no_bubble.scss"],
    },
}
