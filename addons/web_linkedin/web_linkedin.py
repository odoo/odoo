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
from osv import osv, fields

class Binary(openerpweb.Controller):
    _cp_path = "/web_linkedin/binary"

    @openerpweb.jsonrequest
    def url2binary(self, req,url):
        bfile = urllib2.urlopen(url)
        return base64.b64encode(bfile.read())
    
class web_linkedin_settings(osv.osv_memory):
    _name = 'web_linkedin.settings'
    _inherit = 'res.config.settings'
    _columns = {
        'api_key': fields.char(string="API Key", size=50),
        'server_domain': fields.char(size=100),
    }
    
    def get_default_linkedin(self, cr, uid, fields, context=None):
        key = self.pool.get("ir.config_parameter").get_param(cr, uid, "web.linkedin.apikey") or ""
        dom = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        return {'api_key': key, 'server_domain': dom,}
    
    def set_linkedin(self, cr, uid, ids, context=None):
        key = self.browse(cr, uid, ids[0], context)["api_key"] or ""
        self.pool.get("ir.config_parameter").set_param(cr, uid, "web.linkedin.apikey", key)

