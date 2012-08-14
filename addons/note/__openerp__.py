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
==============================================================================

With this module you can allow users to take notes inside OpenERP.
These notes can be shared with OpenERP or external users.
They also can be organized following user dependant categories. 
Notes can be found in the 'Home' main menu, under 'Tool' submenu.
""",
    'author': 'OpenERP SA',
    'website': 'http://openerp.com',
    'depends': ['base_tools','mail','pad'],
    'init_xml': [],
    'update_xml': [
        'security/note_security.xml',
        'security/ir.model.access.csv',
        'note_view.xml',
    ],
    'demo_xml': [
        "note_data.xml"
    ],
    'test':[
    ],
    'css': [
        'static/src/css/note.css',
    ],
    'installable': True,
    'application': True,
    'category': 'Tools',
    'images': [],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
