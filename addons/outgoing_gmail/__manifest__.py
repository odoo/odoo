# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Outgoing Gmail",
    "version": "0.1",
    "category": "Hidden",
    "description": "Google gmail support for outgoing mail servers",
    "depends": [
        "google_gmail",
        "base",
    ],
    "data": ["views/ir_mail_server_views.xml"],
    "installable": True,
    "auto_install": True,
}
