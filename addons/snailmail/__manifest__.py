# -*- coding: utf-8 -*-
{
    'name': "Snail Mail",
    'description': """
Allows users to send documents by post
=====================================================
        """,
    'category': 'Hidden/Tools',
    'version': '0.4',
    'depends': [
        'iap_mail',
        'mail'
    ],
    'data': [
        'data/iap_service_data.xml',
        'data/snailmail_data.xml',
        'views/report_assets.xml',
        'views/snailmail_views.xml',
        'wizard/snailmail_letter_format_error_views.xml',
        'wizard/snailmail_letter_missing_required_fields_views.xml',
        'security/ir.model.access.csv',
    ],
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'snailmail/static/src/**/*',
        ],
        'snailmail.report_assets_snailmail': [
            ('include', 'web._assets_helpers'),
            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',
            'web/static/lib/bootstrap/scss/_variables-dark.scss',
            'web/static/lib/bootstrap/scss/_maps.scss',
        ],
        'web.assets_unit_tests': [
            'snailmail/static/tests/**/*',
        ],
    },
    'license': 'LGPL-3',
}
