# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Website Jitsi",
    "summary": "Create Jitsi room on website.",
    "description": "Create Jitsi room on website.",
    "version": "0.1",
    "depends": ["website"],
    "data": [
        "security/ir.model.access.csv",
        "views/chat_room_templates.xml",
        "views/chat_room_views.xml",
        "views/assets.xml",
    ],
}
