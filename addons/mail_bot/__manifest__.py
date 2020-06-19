# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'OdooBot',
    'version': '1.1',
    'category': 'Productivity/Discuss',
    'summary': 'Add OdooBot in discussions',
    'description': "",
    'website': 'https://www.odoo.com/page/discuss',
    'depends': ['mail'],
    'installable': True,
    'application': False,
    'data': [
        'views/assets.xml',
        'views/res_users_views.xml',
        'data/mailbot_data.xml',
    ],
    'demo': [
        'data/mailbot_demo.xml',
    ],
    'qweb': [
        'static/src/bugfix/bugfix.xml',
        'static/src/components/messaging_menu/messaging_menu.xml',
        'static/src/components/notification_alert/notification_alert.xml',
        'static/src/components/notification_list/notification_list.xml',
        'static/src/components/notification_request/notification_request.xml',
    ],
}
