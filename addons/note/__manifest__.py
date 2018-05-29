# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Productivity',
    'version': '1.0',
    'category': 'Tools',
    'description': "",
    'website': 'https://www.odoo.com/page/notes',
    'summary': 'Notes, Reminders, Todos',
    'sequence': 45,
    'depends': [
        'mail',
    ],
    'data': [
        'security/note_security.xml',
        'security/ir.model.access.csv',
        'data/mail_activity_data.xml',
        'data/note_data.xml',
        'data/res_users_data.xml',
        'views/note_views.xml',
        'views/note_templates.xml',
        'views/mail_activity_views.xml',
    ],
    'demo': [
        'data/note_demo.xml',
    ],
    'qweb': [
        'static/src/xml/systray.xml',
    ],
    'test': [
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
