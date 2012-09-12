# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'Notes',
    'version': '0.1',
    'category': 'Tools',
    'description': """
This module allows users to create their own notes inside OpenERP
=================================================================

Use notes to write meeting minutes, organize ideas, organize personnal todo
lists, etc. Each user manages his own personnal notes. Notes are available to
their authors only, but they can share notes to others users so that several
people can work on the same note in real time. It's very efficient to share
meeting minutes.

Notes can be found in the 'Home' menu.
""",
    'author': 'OpenERP SA',
    'website': 'http://openerp.com',
    'summary': 'Sticky Notes, Collaborative',
    'depends': [
        'base_tools',
        'mail',
        'pad',
    ],
    'data': [
        'security/note_security.xml',
        'security/ir.model.access.csv',
        'note_data.xml',
        'note_view.xml',
    ],
    'demo': [
        'note_demo.xml',
    ],
    'css': [
        'static/src/css/note.css',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
