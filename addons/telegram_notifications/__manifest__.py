# -*- coding: utf-8 -*-
{
    'name': 'Telegram Notifications',
    'version': '1.0',
    'category': 'Tools',
    'summary': 'Receive notifications via Telegram instead of email',
    'author': 'Your Name',
    'depends': ['base', 'mail'],
    'external_dependencies': {
        'python': ['requests'],
    },
    'data': [
        'security/ir.model.access.csv',
        'views/telegram_settings_view.xml',
        'data/telegram_notification_template.xml',
    ],
    'installable': True,
    'application': True,
}