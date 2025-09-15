# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Cloud Storage",
    "summary": """Store chatter attachments in the cloud""",
    "category": "Technical Settings",
    "version": "1.0",
    "depends": ["base_setup", "mail"],
    "data": [
        "views/settings.xml",
    ],
    'assets': {
        "mail.assets_core_common": [
            "cloud_storage/static/src/core/common/**/*",
        ],
        "mail.assets_feature_web_portal": [
            "cloud_storage/static/src/**/web_portal/**/*",
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
