# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Cloud Storage Google",
    "summary": """Store chatter attachments in the Google cloud""",
    "category": "Technical Settings",
    "version": "1.0",
    "depends": ["cloud_storage"],
    "data": [
        "views/settings.xml",
    ],
    'assets': {
        'web.assets_backend': [
            'cloud_storage_google/static/src/**/*',
        ],
    },
    "uninstall_hook": "uninstall_hook",
    'license': 'LGPL-3',
}
