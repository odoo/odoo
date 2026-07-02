# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Portal Discuss",
    "category": "Services",
    "description": "Bridge module adding Discuss access from portal.",
    "depends": ["mail", "portal"],
    "data": [
        "data/portal_entry_data.xml",
        "views/portal_templates.xml",
    ],
    "assets": {
        "mail.assets_public": [
            "portal_discuss/static/src/discuss_client_action_patch.js",
        ],
    },
    "auto_install": True,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
