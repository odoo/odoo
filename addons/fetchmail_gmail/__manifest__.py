# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Fetchmail Gmail",
    "version": "0.1",
    "category": "Hidden",
    "description": "Google authentication for fetch mail",
    "depends": [
        "google_gmail",
        "fetchmail",
    ],
    "data": ["views/fetchmail_server_views.xml"],
    "auto_install": True,
    "license": "OEEL-1",
}
