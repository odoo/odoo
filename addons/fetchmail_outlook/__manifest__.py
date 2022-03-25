# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Fetchmail Outlook",
    "version": "1.0",
    "category": "Hidden",
    "description": "OAuth authentication for incoming Outlook mail server",
    "depends": [
        "microsoft_outlook",
        "fetchmail",
    ],
    "data": [
        "views/fetchmail_server_views.xml",
    ],
    "auto_install": True,
}
