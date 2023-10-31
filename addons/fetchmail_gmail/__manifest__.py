# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Fetchmail Gmail",
    "version": "1.0",
    "category": "Hidden",
    "description": "Google authentication for incoming mail server",
    "depends": [
        "google_gmail",
        "fetchmail",
    ],
    "data": ["views/fetchmail_server_views.xml"],
    "auto_install": True,
    "license": "LGPL-3",
}
