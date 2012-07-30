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
import base64
import urllib2
import xmlrpclib
import zlib


from web import common
openerpweb = common.http

from osv import fields, osv

class company(osv.osv):
    _inherit = 'res.company'
    _columns = {
            'linkedin_api_key': fields.char('LinkedIn API key', size=128),
    }

company()

class users(osv.osv):
    _inherit = 'res.users'
    
    def set_linkedin_api_key(self, cr, uid, key, context=None):
        company_obj = self.pool.get('res.company')
        company_id = company_obj._company_default_get(cr, uid, 'res.users', context=context)
        company_obj.write(cr, uid, [company_id], {'linkedin_api_key': key })
        ir_values = self.pool.get('ir.values')
        ir_values.set_default(cr, uid, 'res.company', 'linkedin_api_key', key)

        return True
users()

class res_partner(osv.osv):
     _inherit = 'res.partner'

     _columns = {
     }

res_partner()

# don't know yet if I will remove it
class Binary(openerpweb.Controller):
    _cp_path = "/web_linkedin/binary"

    @openerpweb.jsonrequest
    def url2binary(self, req,url):
        bfile = urllib2.urlopen(url)
        return base64.b64encode(bfile.read())

