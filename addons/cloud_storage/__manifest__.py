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
        'web.assets_backend': [
            'cloud_storage/static/src/core/common/**/*',
            'cloud_storage/static/src/**/web_portal/**/*',
        ],
        'mail.assets_public': [
            'cloud_storage/static/src/core/common/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
