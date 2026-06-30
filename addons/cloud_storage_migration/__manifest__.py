# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Cloud Storage Migration",
    "summary": """Migrate local attachments to cloud storage""",
    "category": "Technical Settings",
    "version": "1.0",
    "depends": ["cloud_storage"],
    "data": [
        "security/ir.model.access.csv",
        "data/data.xml",
        "data/ir_cron.xml",
        "views/cloud_storage_migration_report_views.xml",
        "views/res_config_settings.xml",
    ],
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
