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
        'mail.assets_discuss_public': [
            'snailmail/static/src/components/*/*',
            'snailmail/static/src/models/*/*.js',
        ],
        'snailmail.report_assets_snailmail': [
            ('include', 'web._assets_helpers'),
            'web/static/lib/bootstrap/scss/_variables.scss',
            'snailmail/static/src/scss/snailmail_external_layout_asset.scss',
            'snailmail/static/src/js/snailmail_external_layout.js',
        ],
        'web.assets_backend': [
            'snailmail/static/src/components/*/*.js',
            'snailmail/static/src/components/*/*.scss',
            'snailmail/static/src/models/*/*.js',
        ],
        'web.tests_assets': [
            'snailmail/static/tests/**/*',
        ],
        'web.qunit_suite_tests': [
            'snailmail/static/src/components/*/tests/*.js',
        ],
        'web.assets_qweb': [
            'snailmail/static/src/components/*/*.xml',
        ],
    },
    'license': 'LGPL-3',
}
