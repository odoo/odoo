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
            'default_linkedin_api_key': fields.char('LinkedIn API key', size=128),
    }

company()

class res_partner(osv.osv):
     _inherit = 'res.partner'

     _columns = {
        'linkedin_id': fields.char('Linkedin Id', size=64),
        'twitter_id': fields.char('Twitter', size=128),
        'profile_id': fields.char('Profile URL', size=240),
     }

     def fields_view_get(self, cr, user, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
         company_obj = self.pool.get('res.company')
         res = super(res_partner, self).fields_view_get(cr, user, view_id, view_type, context, toolbar=toolbar, submenu=submenu)
         company_id = company_obj._company_default_get(cr, user, 'res.users', context=context)
         linkedin_api_key = company_obj.browse(cr, user, company_id, context=context).default_linkedin_api_key
         fields = res['fields']
         if fields.get('name'):
             ctx = fields.get('name').get('context')
             if ctx is None:
                 ctx = {}
             ctx.update({'api_key': linkedin_api_key})
             fields.get('name')['context'] = ctx
         return res

res_partner()

class Binary(openerpweb.Controller):
    _cp_path = "/web_linkedin/binary"

    @openerpweb.jsonrequest
    def url2binary(self, req,url):
        bfile = urllib2.urlopen(url)
        return base64.b64encode(bfile.read())

class Database(openerpweb.Controller):
    _cp_path = "/web_linkedin/database"
    
    @openerpweb.jsonrequest
    def api_key(self, req, key):  
                             
        return True
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
