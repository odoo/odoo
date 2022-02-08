# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'SMS gateway',
    'version': '2.2',
    'category': 'Hidden/Tools',
    'summary': 'SMS Text Messaging',
    'description': """
This module gives a framework for SMS text messaging
----------------------------------------------------

The service is provided by the In App Purchase Odoo platform.
""",
    'depends': [
        'base',
        'iap_mail',
        'mail',
        'phone_validation'
    ],
    'data': [
        'data/ir_cron_data.xml',
        'wizard/sms_cancel_views.xml',
        'wizard/sms_composer_views.xml',
        'wizard/sms_template_preview_views.xml',
        'wizard/sms_resend_views.xml',
        'views/ir_actions_views.xml',
        'views/mail_notification_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/sms_sms_views.xml',
        'views/sms_template_views.xml',
        'security/ir.model.access.csv',
        'security/sms_security.xml',
    ],
    'demo': [
        'data/sms_demo.xml',
        'data/mail_demo.xml',
    ],
    'installable': True,
    'auto_install': True,
    'assets': {
        'mail.assets_discuss_public': [
            'sms/static/src/components/*/*',
            'sms/static/src/models/*/*.js',
        ],
        'web.assets_backend': [
            'sms/static/src/js/fields_phone_widget.js',
            'sms/static/src/js/fields_sms_widget.js',
            'sms/static/src/components/*/*.js',
            'sms/static/src/models/*/*.js',
        ],
        'web.qunit_suite_tests': [
            'sms/static/tests/sms_widget_test.js',
            'sms/static/src/components/*/tests/*.js',
        ],
        'web.assets_qweb': [
            'sms/static/src/components/*/*.xml',
        ],
    },
    'license': 'LGPL-3',
}
