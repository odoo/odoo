# -*- coding: utf-8 -*-
{
    'name': "mail_bot_hr",
    'summary': """Bridge module between hr and mailbot.""",
    'description': """This module adds the OdooBot state and notifications in the user form modified by hr.""",
    'website': "https://www.odoo.com/page/discuss",
    'category': 'Productivity/Discuss',
    'version': '1.0',
    'depends': ['mail_bot', 'hr'],
    'application': False,
    'installable': True,
    'auto_install': True,
    'data': [
        'views/res_users_views.xml',
    ],
    'license': 'LGPL-3',
}
