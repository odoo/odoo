{
    'name': 'Twilio SMS',
    'version': '1.0',
    'summary': 'Send SMS messages using Twilio',
    'category': 'Hidden/Tools',
    'description': """
This module allows using Twilio as a provider for SMS messaging.
The user has to create an account on twilio.com and top
up their account to start sending SMS messages.
""",
    'depends': [
        'sms',
    ],
    'data': [
        'views/res_config_settings_views.xml',
        'views/sms_sms_views.xml',
        'wizard/sms_twilio_account_manage_views.xml',
        'security/ir.model.access.csv'
    ],
    'installable': True,
    'license': 'LGPL-3',
}
