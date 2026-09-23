{
    "name": "KPI Digests",
    "version": "1.2",
    "category": "Marketing",
    "description": """
Send KPI Digests periodically
=============================
""",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "portal",
        "resource",
    ],
    "data": [
        "security/ir.access.csv",
        "data/digest_data.xml",
        "data/digest_tips_data.xml",
        "data/ir_cron_data.xml",
        "data/res_config_settings_data.xml",
        "views/digest_views.xml",
        "views/digest_templates.xml",
        "views/res_config_settings_views.xml",
        "views/digest_menus.xml",
    ],
}
