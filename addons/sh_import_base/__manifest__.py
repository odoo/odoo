# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
{
    "name": "Schedule Import | Import Base",
    "author": "Softhealer Technologies",
    "website": "https://www.softhealer.com",
    "support": "support@softhealer.com",
    "category": "Extra Tools",
    "summary": "Import By Scheduler Import Using Scheduler Import Records Scheduler Import Records Run Scheduler Scheduled Import Schedule Importing Force Import Records Force Import Odoo",
    "description": """This base module useful to import records using schedule import.""",
    "version": "16.0.2",
    "depends": ['base_setup', 'mail', 'mail_bot', 'mail_group'],
    "application": True,
    "data": [
        "security/ir.model.access.csv",
        "security/security.xml",
        "views/sh_import_base_views.xml",
        "views/sh_import_store_views.xml",
    ],
    'assets': {
        'web.assets_backend': [
            "sh_import_base/static/src/import_base.scss",
        ],
    },
    "images": ["static/description/background.png", ],
    "license": "OPL-1",
    "auto_install": False,
    "installable": True,
}
