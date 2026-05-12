# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Mail Inbox',
    'version': '1.0',
    'category': 'Productivity',
    'sequence': 140,
    'summary': 'Manage your email inbox directly in Odoo',
    'description': 'Synchronize your email inbox with Odoo. Browse, star, reply and link emails to your records.',
    'depends': ['mail'],
    'application': True,
    'data': [
        'security/ir.model.access.csv',
        'security/mail_inbox_security.xml',
        'views/fetchmail_server_views.xml',
        'views/fetchmail_mail_views.xml',
        'views/menu.xml',
    ],
    'demo': [
        'demo/fetchmail_mail_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'mail_inbox/static/src/inbox_app.js',
            'mail_inbox/static/src/inbox_app.xml',
            'mail_inbox/static/src/inbox_sidebar.js',
            'mail_inbox/static/src/inbox_sidebar.xml',
            'mail_inbox/static/src/inbox_list.js',
            'mail_inbox/static/src/inbox_list.xml',
            'mail_inbox/static/src/inbox_mail_item.js',
            'mail_inbox/static/src/inbox_mail_item.xml',
            'mail_inbox/static/src/inbox.css',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
