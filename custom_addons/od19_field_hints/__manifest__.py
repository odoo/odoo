# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

{
    "name": "OD19 Field Hints",
    "version": "19.0.1.0.0",
    "author": "OD19",
    "category": "Productivity",
    "summary": "ข้อความตัวอย่าง/คำแนะนำ/คำเตือนสีเทาในช่องกรอกของ Odoo 19",
    "license": "LGPL-3",
    "depends": ["base_setup", "web"],
    "data": [
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "od19_field_hints/static/src/scss/od19_field_hints.scss",
            "od19_field_hints/static/src/js/od19_field_hints.js",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
