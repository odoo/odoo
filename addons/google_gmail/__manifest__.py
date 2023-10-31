# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Google Gmail",
    "version": "1.0",
    "category": "Hidden",
    "description": "Gmail support for incoming / outgoing mail servers",
    "depends": [
        "mail",
        "google_account",
    ],
    "data": [
        "views/ir_mail_server_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "auto_install": True,
    "license": "LGPL-3",
}
