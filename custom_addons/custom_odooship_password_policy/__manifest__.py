# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Password Policy",
    "summary": "Allow admin to set password security requirements.",
    "version": "17.0.0.1",
    "author": "Drishti Joshi",
    "category": "Base",
    "description": """The Password Policy module enforces customizable password security rules, 
    including strength requirements, expiration notifications, and password history restrictions, 
    ensuring enhanced authentication security in Odoo.""",

    "depends": ["auth_signup", "auth_password_policy_signup", "auth_password_policy"],
    'company': 'Shiperoo',
    "license": "LGPL-3",
    "data": [
        "data/cron_send_mail.xml",
        "views/password_expire_notification_templates.xml",
        "views/res_config_settings_views.xml",
        "views/signup_templates.xml",
        "security/ir.model.access.csv",
        "security/res_users_pass_history.xml",
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
