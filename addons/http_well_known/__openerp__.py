# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010 OpenERP s.a. (<http://openerp.com>).
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
    "name" : "Publish well-known http URIs",
    "version" : "0.1",
    "depends" : [ "base", ],
    'description': """
    Implements IETF RFC 5785 for services discovery on a http server.

    May help some CalDAV clients bootstrap from the OpenERP server.

    Note that it needs explicit configuration in openerp-server.conf .
""",
    "author" : "OpenERP SA",
    'category': 'Generic Modules/Others',
    'website': 'http://www.openerp.com',
    "init_xml" : [ ],
    "demo_xml" : [],
    "update_xml" : [ ],
    "installable" : True,
    "active" : False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
