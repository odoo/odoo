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

try:
    # embedded
    import openerp.addons.web.common.http as openerpweb
except ImportError:
    # standalone
    import web.common.http as openerpweb

import base64
import urllib2

class Binary(openerpweb.Controller):
    _cp_path = "/web_linkedin/binary"

    @openerpweb.jsonrequest
    def url2binary(self, req,url):
        bfile = urllib2.urlopen(url)
        return base64.b64encode(bfile.read())

