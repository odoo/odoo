##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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
    "name" : "Authenticate users with LDAP server",
    "version" : "0.1",
    "depends" : ["base"],
    "images" : ["images/ldap_configuration.jpeg"],
    "author" : "OpenERP SA",
    "description": """
Adds support for authentication by LDAP server.
===============================================

This module only works with Unix/Linux.
    """,


    "website" : "http://www.openerp.com",
    "category" : "Tools",
    "init_xml" : [
    ],
    "demo_xml" : [
    ],
    "update_xml" : [
        "users_ldap_view.xml",
    ],
    "active": False,
    "installable": True,
    "certificate" : "001141446349334700221",
    "external_dependencies" : {
        'python' : ['ldap'],
    }
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

