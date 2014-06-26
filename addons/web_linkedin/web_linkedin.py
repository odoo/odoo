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
from urlparse import urlparse, urlunparse

import openerp
import openerp.addons.web
from openerp.osv import fields, osv

class Binary(openerp.http.Controller):
    @openerp.http.route('/web_linkedin/binary/url2binary', type='json', auth='user')
    def url2binary(self, url):
        """Used exclusively to load images from LinkedIn profiles, must not be used for anything else."""
        _scheme, _netloc, path, params, query, fragment = urlparse(url)
        # media.linkedin.com is the master domain for LinkedIn media (replicated to CDNs),
        # so forcing it should always work and prevents abusing this method to load arbitrary URLs
        url = urlunparse(('http', 'media.linkedin.com', path, params, query, fragment))
        bfile = urllib2.urlopen(url)
        return base64.b64encode(bfile.read())
    
class web_linkedin_settings(osv.osv_memory):
    _inherit = 'sale.config.settings'
    _columns = {
        'api_key': fields.char(string="API Key", size=50),
        'server_domain': fields.char(),
    }
    
    def get_default_linkedin(self, cr, uid, fields, context=None):
        key = self.pool.get("ir.config_parameter").get_param(cr, uid, "web.linkedin.apikey") or ""
        dom = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        return {'api_key': key, 'server_domain': dom,}
    
    def set_linkedin(self, cr, uid, ids, context=None):
        key = self.browse(cr, uid, ids[0], context)["api_key"] or ""
        self.pool.get("ir.config_parameter").set_param(cr, uid, "web.linkedin.apikey", key, groups=['base.group_users'])

class web_linkedin_fields(osv.Model):
    _inherit = 'res.partner'

    def _get_url(self, cr, uid, ids, name, arg, context=None):
        res = dict((id, False) for id in ids)
        for partner in self.browse(cr, uid, ids, context=context):
            res[partner.id] = partner.linkedin_url
        return res

    def linkedin_check_similar_partner(self, cr, uid, linkedin_datas, context=None):
        res = []
        res_partner = self.pool.get('res.partner')
        for linkedin_data in linkedin_datas:
            partner_ids = res_partner.search(cr, uid, ["|", ("linkedin_id", "=", linkedin_data['id']), 
                    "&", ("linkedin_id", "=", False), 
                    "|", ("name", "ilike", linkedin_data['firstName'] + "%" + linkedin_data['lastName']), ("name", "ilike", linkedin_data['lastName'] + "%" + linkedin_data['firstName'])], context=context)
            if partner_ids:
                partner = res_partner.read(cr, uid, partner_ids[0], ["image", "mobile", "phone", "parent_id", "name", "email", "function", "linkedin_id"], context=context)
                if partner['linkedin_id'] and partner['linkedin_id'] != linkedin_data['id']:
                    partner.pop('id')
                if partner['parent_id']:
                    partner['parent_id'] = partner['parent_id'][0]
                for key, val in partner.items():
                    if not val:
                        partner.pop(key)
                res.append(partner)
            else:
                res.append({})
        return res

    _columns = {
        'linkedin_id': fields.char(string="LinkedIn ID"),
        'linkedin_url': fields.char(string="LinkedIn url", store=True),
        'linkedin_public_url': fields.function(_get_url, type='text', string="LinkedIn url", 
            help="This url is set automatically when you join the partner with a LinkedIn account."),
    }
