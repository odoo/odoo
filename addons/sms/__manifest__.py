{
    "name": "SMS gateway",
    "version": "3.1",
    "category": "Sales/Sales",
    "summary": "SMS Text Messaging",
    "description": """
This module gives a framework for SMS text messaging
----------------------------------------------------

The service is provided by the In App Purchase Odoo platform.
""",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "base",
        "iap_mail",
        "mail",
        "phone_validation",
    ],
    "data": [
        "data/iap_service_data.xml",
        "data/ir_cron_data.xml",
        "wizards/sms_account_code_views.xml",
        "wizards/sms_account_phone_views.xml",
        "wizards/sms_account_sender_views.xml",
        "wizards/sms_composer_views.xml",
        "wizards/sms_template_preview_views.xml",
        "wizards/sms_template_reset_views.xml",
        "views/ir_actions_server_views.xml",
        "views/mail_notification_views.xml",
        "views/res_config_settings_views.xml",
        "views/res_partner_views.xml",
        "views/iap_account_views.xml",
        "views/sms_sms_views.xml",
        "views/sms_template_views.xml",
        "security/ir.model.access.csv",
        "security/sms_security.xml",
        "views/sms_menus.xml",
    ],
    "demo": [
        "demo/sms_demo.xml",
        "demo/mail_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "sms/static/src/**/*",
        ],
        "web.assets_unit_tests": [
            "sms/static/tests/**/*",
        ],
    },
    "auto_install": True,
}
