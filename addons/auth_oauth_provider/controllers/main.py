# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-2012 OpenERP s.a. (<http://openerp.com>).
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

#import oauth.oauth as oauth
try:
    import openerp.addons.web.common.http as openerpweb
except ImportError:
    import web.common.http as openerpweb

import openerp.modules.registry
from openerp import SUPERUSER_ID

import simplejson
import werkzeug
import urllib

class AuthOAuthProvider(openerpweb.Controller):
    _cp_path = '/oauth2'

    @openerpweb.httprequest
    def auth(self, req, **kw):
        search = req.params.copy()
        if req.debug:
            search['debug'] = 1
        redirect_url = '/?' + urllib.urlencode(search) + '#action=oauth2_auth'
        return werkzeug.utils.redirect(redirect_url, 303)

    @openerpweb.jsonrequest
    def get_token(self, req, client_id="", scope="", **kw):
        token = req.session.model('res.users').auth_oauth_provider_get_token(client_id, scope)
        return {
            'access_token': token,
        }

    @openerpweb.httprequest
    def tokeninfo(self, req, dbname=None, access_token=None, **kw):
        if not dbname or not access_token:
            return simplejson.dumps({ "error": "No 'dbname' or 'access_token' url parameters specified." })
        try:
            registry = openerp.modules.registry.RegistryManager.get(dbname)
            with registry.cursor() as cr:
                u = registry.get('res.users')
                info = u.auth_oauth_provider_tokeninfo(cr, SUPERUSER_ID, access_token, kw)
                return simplejson.dumps(info)
        except Exception, e:
            return simplejson.dumps({ "error": e.message })

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
