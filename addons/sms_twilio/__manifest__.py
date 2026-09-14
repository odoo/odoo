{
    "name": "Twilio SMS",
    "version": "1.2",
    "category": "Hidden/Tools",
    "summary": "Send SMS messages using Twilio",
    "description": """
This module allows using Twilio as a provider for SMS messaging.
The user has to create an account on twilio.com and top
up their account to start sending SMS messages.
""",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "credential",
        "integration",
        "sms",
    ],
    "data": [
        "views/res_config_settings_views.xml",
        "views/sms_sms_views.xml",
        "wizards/sms_twilio_account_manage_views.xml",
        "security/ir.model.access.csv",
    ],
}
