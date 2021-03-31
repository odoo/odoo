# -*- coding: utf-8 -*-
{
    'name': "Snail Mail",
    'description': """
Allows users to send documents by post
=====================================================
        """,
    'category': 'Hidden/Tools',
    'version': '0.3',
    'depends': [
        'iap_mail',
        'mail'
    ],
    'data': [
        'data/snailmail_data.xml',
        'views/report_assets.xml',
        'views/snailmail_views.xml',
        'wizard/snailmail_confirm_views.xml',
        'wizard/snailmail_letter_cancel_views.xml',
        'wizard/snailmail_letter_format_error_views.xml',
        'wizard/snailmail_letter_missing_required_fields_views.xml',
        'security/ir.model.access.csv',
    ],
    'auto_install': True,
    'assets': {
        'snailmail.report_assets_snailmail': [
            ('include', 'web._assets_helpers'),
            'web/static/lib/bootstrap/scss/_variables.scss',
            'snailmail/static/src/scss/snailmail_external_layout_asset.scss',
            'snailmail/static/src/js/snailmail_external_layout.js',
        ],
        'web.assets_backend': [
            'snailmail/static/src/bugfix/bugfix.js',
            'snailmail/static/src/components/message/message.js',
            'snailmail/static/src/components/notification_group/notification_group.js',
            'snailmail/static/src/components/snailmail_error_dialog/snailmail_error_dialog.js',
            'snailmail/static/src/components/snailmail_notification_popover/snailmail_notification_popover.js',
            'snailmail/static/src/models/message/message.js',
            'snailmail/static/src/models/messaging/messaging.js',
            'snailmail/static/src/models/notification_group/notification_group.js',
            'snailmail/static/src/bugfix/bugfix.scss',
            'snailmail/static/src/components/snailmail_notification_popover/snailmail_notification_popover.scss',
        ],
        'web.tests_assets': [
            'snailmail/static/tests/**/*',
        ],
        'web.qunit_suite_tests': [
            'snailmail/static/src/bugfix/bugfix_tests.js',
            'snailmail/static/src/components/message/message_tests.js',
            'snailmail/static/src/components/notification_list/notification_list_notification_group_tests.js',
        ],
        'web.assets_qweb': [
            'snailmail/static/src/bugfix/bugfix.xml',
            'snailmail/static/src/components/message/message.xml',
            'snailmail/static/src/components/notification_group/notification_group.xml',
            'snailmail/static/src/components/snailmail_error_dialog/snailmail_error_dialog.xml',
            'snailmail/static/src/components/snailmail_notification_popover/snailmail_notification_popover.xml',
        ],
    }
}
