# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'SMS gateway',
    'version': '2.0',
    'category': 'Tools',
    'summary': 'SMS Text Messaging',
    'description': """
This module gives a framework for SMS text messaging
----------------------------------------------------

The service is provided by the In App Purchase Odoo platform.
""",
    'depends': ['base', 'iap', 'mail', 'phone_validation'],
    'data': [
        'data/ir_cron_data.xml',
        'wizard/sms_cancel_views.xml',
        'wizard/sms_composer_views.xml',
        'wizard/sms_template_preview_views.xml',
        'wizard/sms_resend_views.xml',
        'views/ir_actions_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/assets.xml',
        'views/sms_sms_views.xml',
        'views/sms_template_views.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
        'data/sms_demo.xml',
        'data/mail_demo.xml',
    ],
    'qweb': [
        'static/src/xml/thread.xml',
    ],
    'installable': True,
    'auto_install': True,
}
