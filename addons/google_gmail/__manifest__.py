# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Google Gmail",
    "version": "1.3",
    "category": "Hidden",
    "description": "Gmail support for incoming / outgoing mail servers",
    "depends": [
        "mail",
    ],
    "data": [
        "views/fetchmail_server_views.xml",
        "views/ir_mail_server_views.xml",
        "views/res_config_settings_views.xml",
        "security/ir.model.access.csv",
    ],
    "auto_install": True,
    "license": "LGPL-3",
}
