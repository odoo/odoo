# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Productivity',
    'version': '1.0',
    'category': 'Tools',
    'description': """
This module allows users to create their own notes inside Odoo
=================================================================

Use notes to write meeting minutes, organize ideas, organize personal todo
lists, etc. Each user manages his own personal Notes. Notes are available to
their authors only, but they can share notes to others users so that several
people can work on the same note in real time. It's very efficient to share
meeting minutes.

Notes can be found in the 'Home' menu.
""",
    'website': 'https://www.odoo.com/page/notes',
    'summary': 'Sticky notes, Collaborative, Memos',
    'sequence': 45,
    'depends': [
        'mail',
    ],
    'data': [
        'security/note_security.xml',
        'security/ir.model.access.csv',
        'data/note_data.xml',
        'views/note_views.xml',
        'views/note_templates.xml',
    ],
    'demo': [
        'data/note_demo.xml',
    ],
    'test': [
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
