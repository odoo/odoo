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
    "name" : "Share Management",
    "version" : "1.1",
    "depends" : ["base"],
    "author" : "OpenERP SA",
    "category": 'Generic Modules',
    "description": """The goal is to implement a generic sharing mechanism, where user of OpenERP
can share data from OpenERP to their colleagues, customers, or friends.
The system will work by creating new users and groups on the fly, and by
combining the appropriate access rights and ir.rules to ensure that the /shared
users/ will only have access to the correct data.
    """,
    'website': 'http://www.openerp.com',
    'init_xml': [],
    'update_xml': [
        'share_view.xml',
        'wizard/share_wizard_view.xml'
    ],    
    'installable': True,
    'active': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
