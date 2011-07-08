# -*- coding: utf-8 -*-
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

import http_server
import netrpc_server
import web_services

#.apidoc title: RPC Services

""" Classes of this module implement the network protocols that the
    OpenERP server uses to communicate with remote clients.

    Some classes are mostly utilities, whose API need not be visible to
    the average user/developer. Study them only if you are about to
    implement an extension to the network protocols, or need to debug some
    low-level behavior of the wire.
"""

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

