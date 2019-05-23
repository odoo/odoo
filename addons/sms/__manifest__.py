# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'SMS gateway',
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
        'wizard/sms_composer_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/assets.xml',
        'views/sms_sms_views.xml',
        'security/ir.model.access.csv',
    ],
    'qweb': [
        'static/src/xml/sms_widget.xml',
    ],
    'installable': True,
    'auto_install': True,
}
