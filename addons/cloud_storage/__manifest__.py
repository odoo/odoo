# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Cloud Storage",
    "summary": """Store chatter attachments in the cloud""",
    "category": "Technical Settings",
    "depends": ["base_setup", "mail"],
    "data": [
        "views/settings.xml",
    ],
    'assets': {
        'web.assets_backend': [
            'cloud_storage/static/src/core/common/**/*',
            'cloud_storage/static/src/core/public_web/**/*',
            'cloud_storage/static/src/**/web/**/*',
        ],
        'mail.assets_public': [
            'cloud_storage/static/src/core/common/**/*',
            'cloud_storage/static/src/core/public_web/**/*',
        ],
        'portal.assets_chatter_helpers': [
            'cloud_storage/static/src/core/common/**/*',
        ],
        'web.assets_unit_tests': [
            'cloud_storage/static/tests/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
