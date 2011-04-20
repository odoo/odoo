# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2011 Tiny SPRL (<http://tiny.be>).
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
    "name" : "Portal",
    "version" : "0.2",
    "depends" : ["base"],
    "author" : "OpenERP SA",
    "category": 'Tools',
    "description": """
This module defines 'portals' to customize the access to your OpenERP database
for external users.

A portal defines customized user menu and access rights for a group of users
(the ones associated to that portal).  It also associates user groups to the
portal users (adding a group in the portal automatically adds it to the portal
users, etc).  That feature is very handy when used in combination with the
module 'share'.
    """,
    'website': 'http://www.openerp.com',
    'demo_xml': [],
    'data': ['portal_view.xml'],
    'installable': True,
    'certificate' : '',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
