# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Memos pad',
    'version': '0.1',
    'category': 'Productivity/Notes',
    'description': """
This module update memos inside Odoo for using an external pad
=================================================================

Use for update your text memo in real time with the following user that you invite.

""",
    'summary': 'Sticky memos, Collaborative',
    'depends': [
        'mail',
        'pad',
        'note',
    ],
    'data': [
        'views/note_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
    'license': 'LGPL-3',
}
