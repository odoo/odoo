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
    import web.common.http as openerpweb    # noqa

import simplejson


class AuthOAuthProvider(openerpweb.Controller):
    _cp_path = '/oauth2'

    @openerpweb.jsonrequest
    def get_token(self, req, client_id="", scope="", **kw):
        token = req.session.model('res.users').auth_oauth_provider_get_token(client_id, scope)
        return {
            'access_token': token,
        }

    @openerpweb.httprequest
    def tokeninfo(self, req, access_token="", **kw):
        info = req.session.model('res.users').auth_oauth_provider_tokeninfo(access_token)
        return simplejson.dumps(info)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
