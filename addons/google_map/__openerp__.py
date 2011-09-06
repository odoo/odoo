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
    'name': 'Google Map',
    'version': '1.0',
    'category': 'Tools',
    'complexity': "easy",
    'category': 'Generic Modules/Others',
    'description': """
The module adds Google Map field in partner address.
====================================================

Using this you can directly open Google Map from the URL widget.""",
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'images': ['images/google_map.jpeg'],
    'depends': ['base'],
    'init_xml': [],
    'update_xml': ['wizard/google_map_launch_view.xml',
                   'google_map_view.xml',
                  ],
    'demo_xml': [],
    'installable': True,
    'active': False,
    'certificate': '0029498930765',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
