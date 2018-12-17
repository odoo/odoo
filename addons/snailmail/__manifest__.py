# -*- coding: utf-8 -*-
{
    'name': "Snail Mail",
    'description': """
Allows users to send documents by post
=====================================================
        """,
    'category': 'Tools',
    'version': '0.1',
    'depends': ['iap', 'mail'],
    'data': [
        'data/snailmail_data.xml',
        'views/report_assets.xml',
        'views/snailmail_views.xml',
        'views/assets.xml',
        'wizard/snailmail_letter_cancel_views.xml',
        'wizard/snailmail_letter_format_error_views.xml',
        'wizard/snailmail_letter_missing_required_fields_views.xml',
        'security/ir.model.access.csv',
    ],
    'qweb': [
        'static/src/xml/thread.xml',
    ],
    'auto_install': True,
}
