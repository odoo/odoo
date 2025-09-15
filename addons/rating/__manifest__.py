# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Customer Rating',
    'version': '1.1',
    'category': 'Productivity',
    'description': """
This module allows a customer to give rating.
""",
    'depends': [
        'mail',
    ],
    'data': [
        'views/rating_rating_views.xml',
        'views/rating_templates.xml',
        'views/mail_message_views.xml',
        'security/ir.model.access.csv'
    ],
    'installable': True,
    'assets': {
        "mail.assets_core_common": [
            "rating/static/src/core/common/**/*",
        ],
        "mail.assets_core_public_web": [
            "rating/static/src/core/public_web/**/*",
        ],
        'web.assets_frontend': [
            'rating/static/src/scss/rating_templates.scss',
        ],
        'web.assets_unit_tests': [
            'rating/static/tests/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
