# -*- coding: utf-8 -*-
{
    'name': 'Customer Rating',
    'version': '1.0',
    'category': 'Productivity',
    'description': """
This module allows a customer to give rating.
""",
    'depends': [
        'mail',
    ],
    'data': [
        'views/rating_rating_views.xml',
        'views/rating_template.xml',
        'views/mail_message_views.xml',
        'security/ir.model.access.csv'
    ],
    'installable': True,
    'auto_install': False,
    'assets': {
        'web.assets_backend': [
            'rating/static/src/models/message/message.js',
        ],
        'web.assets_frontend': [
            'rating/static/src/scss/**/*',
        ],
        'web.assets_qweb': [
            'rating/static/src/components/thread_needaction_preview/thread_needaction_preview.xml',
            'rating/static/src/components/thread_preview/thread_preview.xml',
        ],

    }
}
