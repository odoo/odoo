{
    'name': 'SMS Message Tracking',
    'summary': 'Track source of messages by sms',
    'category': 'Productivity/Discuss',
    'depends': [
        'mail_tracking',
        'sms',
    ],
    'data': [
        'views/mail_message_views.xml',
    ],
    'author': 'Odoo S.A.',
    'auto_install': True,
    'license': 'LGPL-3',
}
